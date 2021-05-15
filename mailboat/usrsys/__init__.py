# Copyright (C) 2021 The Mailboat Contributors
#
# This file is part of Mailboat.
#
# Mailboat is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Mailboat is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Mailboat.  If not, see <http://www.gnu.org/licenses/>.

"""The user system for Mailboat.

User system process all the things about users:

- User and Profile
- Authentication
- Mailboxes

## User and Profile: The differences
Mailboat defines two structures for user infomation: `usr.UserRecord` and `usr.ProfileRecord`.
`usr.UserRecord` stores infomation which about the "User", which is about mailboat's daily running: username, password...
`usr.ProfileRecord` stores infomation about people: public name, age, sex...
"""
