#!/bin/bash

cd /tmp

git clone --depth=1 -b v0.23.4 https://github.com/libgit2/libgit2.git
cd libgit2

mkdir build
cd build
cmake ..
sudo cmake --build . --target install
