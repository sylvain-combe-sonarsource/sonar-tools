
:: sonar-tools
:: Copyright (C) 2022 Olivier Korach
:: mailto:olivier.korach AT gmail DOT com
::
:: This program is free software; you can redistribute it and/or
:: modify it under the terms of the GNU Lesser General Public
:: License as published by the Free Software Foundation; either
:: version 3 of the License, or (at your option) any later version.
::
:: This program is distributed in the hope that it will be useful,
:: but WITHOUT ANY WARRANTY; without even the implied warranty of
:: MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
:: Lesser General Public License for more details.
::
:: You should have received a copy of the GNU Lesser General Public License
:: along with this program; if not, write to the Free Software Foundation,
:: Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
::

:: build_docs=1
:: release=0

black --line-length=150 .
rmdir /S /Q build
rmdir /S /Q dist
python setup.py bdist_wheel

:: Deploy locally for tests
echo y | pip uninstall sonar-tools
pip install dist/sonar_tools-2.4-py3-none-any.whl

:: sphinx-build -b html api-doc/source api-doc/build

set SONAR_HOST_URL=http://localhost:9999
set SONAR_TOKEN=squ_0172c821af007e813159d6f051f9a726cd3dbdaf

:: Deploy on pypi.org once released
::if [ "$release" = "1" ]; then
::    echo "Confirm release [y/n] ?"
::    read confirm
::    if [ "$confirm" = "y" ]; then
::        python3 -m twine upload dist/*
::    fi
::fi