# Copyright 2022 Jussi Pakkanen

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import sys
import os
import pathlib
import json
import platform
import tempfile
import subprocess

bat_template = '''@ECHO OFF

call "{}"

ECHO {}
SET
'''

prefix = '''#include<windows.h>
#include<winbase.h>
#include<stdio.h>
#include<string>

int main(int argc, char **argv) {
'''

suffix = '''
    const std::string cmdline = GetCommandLineA();
    //printf("In-command: %s\\n", cmdline.c_str());
    const auto space_loc = cmdline.find(' '); // Assumes that the executable path does not have a space in it.
    std::string invocation{"cl "};
    invocation += cmdline.substr(space_loc);
    //printf("Out-command: %s\\n", invocation.c_str());

    STARTUPINFO si;
    PROCESS_INFORMATION pi;
    SECURITY_ATTRIBUTES sec;
    DWORD exit_code;

    ZeroMemory( &si, sizeof(si) );
    si.cb = sizeof(si);
    ZeroMemory( &pi, sizeof(pi) );
    sec.nLength = sizeof(SECURITY_ATTRIBUTES);
    sec.lpSecurityDescriptor = nullptr;
    sec.bInheritHandle = TRUE;
    if(!CreateProcess(nullptr, (LPSTR)invocation.c_str(), &sec, &sec, TRUE, 0, nullptr, nullptr, &si, &pi)) {
        return 1;
    }
    WaitForSingleObject(pi.hProcess, INFINITE);
    GetExitCodeProcess(pi.hProcess, &exit_code);
    CloseHandle(pi.hProcess);
    CloseHandle(pi.hThread);
    return (int)exit_code;
}
'''

def set_up_compiler():
    root = os.environ.get("ProgramFiles(x86)") or os.environ.get("ProgramFiles")
    bat_locator_bin = pathlib.Path(root, 'Microsoft Visual Studio/Installer/vswhere.exe')
    if not bat_locator_bin.exists():
        raise MesonException(f'Could not find {bat_locator_bin}')
    bat_json = subprocess.check_output(
        [
            str(bat_locator_bin),
            '-latest',
            '-prerelease',
            '-requiresAny',
            '-requires', 'Microsoft.VisualStudio.Component.VC.Tools.x86.x64',
            '-requires', 'Microsoft.VisualStudio.Workload.WDExpress',
            '-products', '*',
            '-utf8',
            '-format',
            'json'
        ]
    )
    bat_info = json.loads(bat_json)
    if not bat_info:
        # VS installer instelled but not VS itself maybe?
        raise MesonException('Could not parse vswhere.exe output')
    bat_root = pathlib.Path(bat_info[0]['installationPath'])
    if platform.machine() == 'ARM64':
        bat_path = bat_root / 'VC/Auxiliary/Build/vcvarsx86_arm64.bat'
    else:
        bat_path = bat_root / 'VC/Auxiliary/Build/vcvars64.bat'
        # if VS is not found try VS Express
        if not bat_path.exists():
            bat_path = bat_root / 'VC/Auxiliary/Build/vcvarsx86_amd64.bat'
    if not bat_path.exists():
        sys.exit(f'Could not find {bat_path}')

    bat_separator = '---SPLIT---'
    bat_contents = bat_template.format(bat_path, bat_separator)
    bat_file = tempfile.NamedTemporaryFile('w', suffix='.bat', encoding='utf-8', delete=False)
    bat_file.write(bat_contents)
    bat_file.flush()
    bat_file.close()
    bat_output = subprocess.check_output(bat_file.name, universal_newlines=True)
    os.unlink(bat_file.name)
    bat_lines = bat_output.split('\n')
    bat_separator_seen = False
    src = 'cwrapper.cpp'
    outexe = 'cl-x64.exe'
    with open(src, 'w', encoding='utf-8') as ofile:
        ofile.write(prefix)
        for bat_line in bat_lines:
            if bat_line == bat_separator:
                bat_separator_seen = True
                continue
            if not bat_separator_seen:
                continue
            if not bat_line:
                continue
            try:
                k, v = bat_line.split('=', 1)
            except ValueError:
                # there is no "=", ignore junk data
                pass
            else:
                ofile.write(f'    SetEnvironmentVariable(R"({k})", R"({v})");\n')
                #pass
        ofile.write(suffix)
    subprocess.call(['cl', '/O2', src, '/o' + outexe])

if __name__ == '__main__':
    set_up_compiler()
