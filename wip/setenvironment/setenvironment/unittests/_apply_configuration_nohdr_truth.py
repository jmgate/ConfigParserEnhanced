envvar_op("set","FOO","bar")
envvar_op("append","FOO","baz")
envvar_op("prepend","FOO","foo")
envvar_op("set","BAR","foo")
envvar_op("unset","FOO")
ModuleHelper.module("purge")
ModuleHelper.module("use","setenvironment/unittests/modulefiles")
ModuleHelper.module("load","gcc/4.8.4")
ModuleHelper.module("load","boost/1.10.1")
ModuleHelper.module("load","gcc/4.8.4")
ModuleHelper.module("unload","boost")
ModuleHelper.module("swap","gcc","gcc/7.3.0")


