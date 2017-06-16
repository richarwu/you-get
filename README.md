```you-get``` is inactive for 26 days so perhaps we need a fork.

The branch, named ```master```, is a fork of ```you-get 0.4.750```.

Install:

First, clean up the mess if you tried installing ```you-get``` through ways other than ```pip3```. ```you-get``` is a python 3 package and there's only one correct way to install it. Then:

```
$ pip3 install --upgrade https://github.com/rosynirvana/you-get/archive/master.zip
```

Restore to the upstream develop branch:
```
$ pip3 install --upgrade https://github.com/soimort/you-get/archive/develop.zip
```

Note: There's no ```pip3``` for some python 3 platforms on windows. Try ```pip``` Instead.

---

```you-get```已经有26天没有更新了，或许应该fork一份独立维护。

安装：

首先，如果曾经用```pip3```之外的方法安装过```you-get```，请把环境清理干净。```you-get```是一个python 3的包，用```pip3```之外的方法安装都会带来潜在的麻烦。然后：

```
$ pip3 install --upgrade https://github.com/rosynirvana/you-get/archive/master.zip
```

回复到原本的develop分支：
```
$ pip3 install --upgrade https://github.com/soimort/you-get/archive/develop.zip
```

注意：某些windows下面的python 3环境没有```pip3```，可能是```pip```。
