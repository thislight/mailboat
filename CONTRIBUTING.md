# Contributing

## Development & running environment
Use [poetry](https://python-poetry.org/):
(under project root)
````
poetry install
````

Install git pre-commit hooks:
````
poetry run pre-commit install
````

Then you could prefix your command with `poetry run`:
````shell
poetry run pytest # run test set
````
Or use `poetry shell` for a virtualenv's shell.

## Making contribution to code/docs
Please read "Code" section in this file before writing code for mailboat. If you want to make yourself familiar with the code, turn to "docs/code_guide.md".
Follow the guidelines while you are writing documents (if they have).

1. Fork
2. Work on your fork (`master` or `develop`)
3. Fire a merge request/pull request to `develop` branch

If you have problem with GitHub and comfort to git-email workflow, you can send your patch to maintainer.

After any contributing, you automatically become one of the contributors, but you need to claim yourself in "CONTRIBUTORS" to have the rights.

## Firing issue
Before firing issue, you should look at manual and FAQ.
For security issues, please directly send an email to maintainer, see "CONTRIBUTING.md".

Your issue may contains four parts and should be in English:
* (Required) Your environment: the version of mailboat, the host environment (system version, python version, etc.), the configuration...
* (Required) The problem (What you did; what happen; what your excepted)
* (Recommended) The minial reproduce sample and detailed usage
* (Optional) Your thinks

There are no template, use any way you want to split them out. Add them if you have other things want to write.

Your issue title should claim "the problem" clearly, for example:

Good: "The MTA server crashed by RuntimeError after a normal email came"
Bad: "The MTA server crashed"

Use technical words (if you could) will clear your meaning:

Good: "The emails which send to address suffixed with .org are unexceptedly dropped"
Bad: "The emails which have special pattern are gone.



## Roles
### Maintainer
Maintainer: `Rubicon Rowe <l1589002388@gmail.com>`

Maintainer maintains the status of project. They should respond to issues, merge requests and other things quickly. That's not means they can made every decision for this project: anything could not be ensure should be lead to voting.

* Maintaining issues
* Reviewing & responding merge requests
* Managing versions & release cycle
* Managing project
* NO RESPONSIBLITY to fix problems

### Maintaining developers
There might be multiple maintaining developer. They does not have some key permissions for the project itself which owns by maintainer, for example: deleting repository, but they share responsibilities and permissions on merge requests and issues.

The release cycle is still maintained by maintainer.

* Maintaining issues
* Reviewing & responding merge requests
* NO RESPONSIBLITY to fix problems


## Code
Use "black" to format all code files, including mailboat itself and tests.

## Testing
We use "pytest" as the testing framework. It should be automatically installed when you are installing the development environment by poetry (You need to specify you don't need install them if you don't need, by `--no-dev` option for `poetry install`).

### Performance testing
The test set contains some performance tests, but they are skipped by default because of the high time costs. Set environment variable `TEST_PERFORMANCE` to `1` to run them.

````shell
TEST_PERFORMANCE=1 pytest
````

## Git hooks
There are git hooks could help you maintaining the code quality.

We have switched to use [pre-commit](https://pre-commit.com) as the hooks manager after 7 May 2021.

You could install hooks though the CLI:
````shell
# If you doesn't entered the virtualenv, use "poetry shell"
pre-commit install
````
