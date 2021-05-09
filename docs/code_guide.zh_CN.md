# 代码导览

本导览展示了信舟的代码布局和设计。如果你想贡献这个软件库，推荐同时阅读 "CONTRIBUTING.md"，该文件描述了做贡献的要求。

本导览会随着软件的更新而更新，请仔细检查本手册的最后更新时间；由于软件快速变化，有些内容可能已经过期。我们制作这本手册是希望它能发挥作用，但我们不对其作任何保证；甚至没有隐含的适销性或特定用途的保证。如果你发现手册中有任何问题，可以给我们发一个补丁！

本手册是信舟的一部分，以自由软件基金会发布的GNU通用公共许可证（GNU General Public License）为许可证来分发，适用于该许可证的第3版或任何更高的版本。所有关于本手册的建议都可以发给信舟的问题跟踪器或维护者。

这个导览不是**开发人员手册**，它只包含对代码布局和设计的简要介绍。如果需要查阅更详细的结构、使用方法和提示请阅读开发人员手册（截至2021年5月，该手册仍在编写中）。由于信舟仍在快速开发中，本导览的某些内容可能还无法填充，有些内容可能已经过时，敬请注意。

信舟的命名空间以`mailboat`为根，如信舟下的`usrsys.auth`模块即为`mailboat.usrsys.auth`，本导览中默认省略根。

## 目录
- 核心部分（用户系统、存储层）
- 交互部分（邮件传输代理、邮件用户代理、HTTP应用接口网关）
- 邮件列表和已读跟踪
- 工具包
  - `asec` -- 安全函数包
  - `aspf` -- 异步SPF检查包装
  - `global_executor` -- 全局线程池
  - `perf` -- 运行时性能测量工具

## 核心部分（用户系统、存储层）
用户系统和存储层是信舟的核心部分，存储层包含了抽象存储层以及其实现。

抽象存储层模块在`utils.storage`下，其包含了抽象存储层的工具类和一个基于UnQLite的CommonStorage实现。

### 抽象存储层
信舟的抽象存储层以Record这一概念为中心。Record是抽象存储层中最小可存储的单元，既可以是一个原子类型也可以是一个复合类型（见`RecordStorage`）。

但实际上我们无法安全的保存一个任意复合类型（比如说任何一个Dataclass），于是抽象存储层中增加了一个`RecordStorage`的特例：`CommonStorage`。`CommonStorage`实际上就是一个以字符串类型做键的字典为Record类型的`RecordStorage`。我们也可以在其类型定义中看出这一点：

````python
class CommonStorage(RecordStorage[Dict[str, Any]]):
    pass
````

但是，我们经常希望直接读写一个特定类型而不是一个字典，直接读写一个特定类型可以有更方便的语法和代码补全，但是我们也不希望为每一个新类型都写一个新的Storage类。
此时我们可以注意到`CommonStorage`以字典存储值，而大多数情况下我们的数据也可以直接转换成字典。`utils.storage`为这种用法提供了相应的工具类：`CommonStorageRecordWrapper`，用户只需要提供一个`CommonStorage`和一个负责转换类型的`CommonStorageAdapter`即可创造出一个用特定类型读写Record的`RecordStorage`。

在信舟中，大部分数据结构都用`dataclasses`声明。为方便使用，`utils.storage`直接为其提供了一个`CommonStorageAdapter`的实现：`DataclassCommonStorageAdapter`。

### StorageHub
在根包（`mailboat`，不是`mailboat.mailboat`）中有一个名为`StorageHub`的类，这个类会存放整个Mailboat的存储信息和相应的工具类。

`StorageHub`在未来的版本可能会移动到其它地方。

### 用户系统
信舟的用户系统放在`usrsys`模块下，用户系统是信舟中最复杂的部分之一，它处理用户的信息(User、Profile)、信箱、验证身份的Token。 信舟的用户信息分成User和Profile两部分：User保存跟信舟本身有关的信息，Profile保存跟信舟无关的信息，User和Profile靠Profile ID联系在一起，Profile ID也能标识单个逻辑上的用户（见`UserRecord`和`ProfileRecord`）。

用户系统的存储层实现都放在`usrsys.storage`下。基本都只是使用了`CommonStorageRecordWrapper`再加上一些包装方法。

`usrsys.usr`下是用户系统中几乎所有数据结构的定义。一个特例是`usrsys.tk`下的`TokenRecord`，同时这个包下面还有一个用于处理Token权限的`Scope`工具类。

`usrsys.mailbox`下面的`Mailbox`工具类用于指代一个逻辑邮件箱。

`usrsys.auth`内主要是关于验证用户的工具，`AuthProvider`是一个用于验证用户的工具类。

### `Mailboat`类
在`mailboat`（加上根包名即为`mailboat.mailboat`）下有一个`Mailboat`类，这个类的主要作用是在不同的组件之间作为一个桥梁，将不同的组件组合在一起提供服务。这个类的位置似乎不太合适，也许将会在未来版本中移动到更合适的地方。


## 交互部分（邮件传输代理、邮件用户代理、HTTP应用接口网关）
“交互部分”中的“交互”指的是信舟实例和最终用户的交互。这种交互主要和邮件传输代理、邮件用户代理和HTTP应用接口相关。

### 邮件传输代理
信舟的邮件传输代理放在`mta`模块下。`mta`模块中的`TransferAgent`类是提供给其它部分操作的接口。

目前邮件传输代理只通过第三方库"aiosmtpd"实现了SMTP，相关的东西主要保存在`mta.smtp`下。

`mta.protocols`存放了`mta`里面常用的自定义Protocol类型。

### 邮件用户代理
此部分尚未完成。

### HTTP应用接口网关
此部分尚未完成。

## 邮件列表和已读跟踪
此部分尚未完成。

## 工具包
`utils`模块存放了信舟用到的杂七杂八小工具。

### `asec` -- 安全函数包
`utils.asec`目前主要存放了哈希密码和检查密码的函数。其中带`_sync`的为同步函数，不带的为“异步”函数。
目前信舟中主要使用“异步”函数。“异步”函数实际上就是把同步函数放到线程池中运行，我们应当继续研究其对性能的影响。

请注意：由于Python全局解释锁的限制，在线程池中运行的代码可能仍会阻塞主线程。

### `aspf` -- 异步SPF检查包装
`utils.aspf`是一个对pyspf的简单包装，通过将pyspf放入线程池中运行来避免主线程阻塞。

关于SPF（Sender Policy Framework)的介绍： https://zh.wikipedia.org/wiki/%E5%8F%91%E4%BB%B6%E4%BA%BA%E7%AD%96%E7%95%A5%E6%A1%86%E6%9E%B6

### `global_executor` -- 全局线程池
`utils.global_executor`存放了全局线程池，该线程池将在这个模块下`get`函数第一次调用时创建。

### `perf` -- 运行时性能测量工具
`utils.perf`存放了一些在运行时测量性能的工具：装饰器`perf_point`和`async_perf_point`可用于测量函数的运行时长，结果保存在该模块的`PERF_DATA`下。
