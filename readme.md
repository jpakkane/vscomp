# Making VS compilers runnable from any shell

Start the x64 dev tools shell and run this command:

```
python vscomp.py
```

Then create a new plain command prompt and `cd` into the same
directory.  Then run this to verify:

```
cl-x64 cwrapper.cpp /O2 /osecond.exe
```

You should have a successfully built `second.exe` in the current
output directory. If yes, the compiler is working.

## Bugs

This does not work in MinGW, because it uses an absolute path to the
command file which might have spaces (espcially if doing this in your
home directory). This could be fixed by smarter handling of the return
value of `GetCommandLineA`.

This script could be updated to work with x86 and arm targets. Not
done yet due to laziness. Pull requests welcome.
