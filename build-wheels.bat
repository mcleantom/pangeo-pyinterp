cibuildwheel --platform windows .
@echo off
for %%F in (wheelhouse\*) do (
    python -m delvewheel repair -w wheelhouse "%%F" --add-path vcpkg_installed\x64-windows\bin
)
pause
