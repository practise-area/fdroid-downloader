import os

import logging

import sys

from modules.environment_setuper import EnvironmentSetuper
from modules.json_util import JsonWriter
from modules.entities import Package
from modules.exceptions import FdroidCompilerException
from modules.gradle.gradle_editor import GradleEditor
from modules.instrumentation import InstrumentationHandler
from modules.gradle.apk_assembler import ApkAssembler
from modules.gradle.gradle_project_detector import GradleProjectDetector
from modules.gradle.gradle_version_extractor import GradleVersionExtractor
from modules import util
from modules.manifest import ManifestEditor, Manifest
from conf import config


def main():

    package_names = os.listdir(config.repo_dir)

    with open('done_list.txt', 'a+') as done_list:
        done_list.seek(0)
        done_list_lines = done_list.readlines()
        skip_package_names = [line.split(': ')[0] for line in done_list_lines]
        logging.info('================================================================================================================================================')
        logging.info(f'DONE LIST SIZE: {len(skip_package_names)}')
        logging.debug(f'DONE LIST CONTENT: {skip_package_names}')
        packages = []
        counter = len(done_list_lines)
        done_list.seek(0)
        fail = done_list.read().count('FAIL')
        size = len(package_names)
        package = None
        for name in set(package_names) - set(skip_package_names):
            package_path = config.repo_dir + '\\' + name
            if GradleProjectDetector(package_path).is_gradle_project():
                counter += 1
                try:
                    logging.info('================================================================================================================================================')
                    logging.info(f'{name}: {counter} OF {size}, FAILS={fail}')
                    package = Package(name)

                    EnvironmentSetuper(package).add_local_properties()

                    package.gradle_version = GradleVersionExtractor(package).extract_gradle_version()
                    assembler = ApkAssembler(package)

                    gradle_editor = GradleEditor(package)

                    apk = assembler.assemble_apk(is_instrumented=False)
                    util.move_apk_to_results_dir(apk)

                    manifest = Manifest(package)
                    ManifestEditor(manifest).edit_manifest()

                    InstrumentationHandler(package).add_instrumentation_files()

                    gradle_editor.edit_build_file()

                    instrumented_apk = assembler.assemble_apk(is_instrumented=True)
                    util.move_apk_to_results_dir(instrumented_apk)

                    packages.append(package)
                    logging.info(f'{name}: SUCCESS')
                    done_list.write(f'{name}: SUCCESS\n')
                    done_list.flush()
                except KeyboardInterrupt:
                    logging.info('Keyboard interrupt, revert changes to current project')
                    reset_project_state(package)
                    JsonWriter(packages).save_to_json()
                    sys.exit()
                except (FdroidCompilerException, BaseException):
                    logging.exception(f'{name}: FAIL')
                    fail += 1
                    done_list.write(f'{name}: FAIL\n')
                    done_list.flush()
    JsonWriter(packages).save_to_json()
    logging.info(f'{counter} gradle projects of {size} packages processed, {fail} failed')


def reset_project_state(package):
    os.chdir(package.path)
    os.system('git reset --hard HEAD && git clean -xfd')


if __name__ == '__main__':
    util.setup_logging()
    main()
