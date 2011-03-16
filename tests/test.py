import unittest
import subprocess

class TestJSBorg(unittest.TestCase):

    def compare_command_output_with_file_contents(self, cmd, filename):
        process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
        output = process.communicate()[0]
        self.assertEquals(output,open(filename).read())


    def test_compiles_single_require(self):
        cmd = "python jsborg/jsborg.py tests/js tests/js/test_single_require.js"
        filename = "tests/js/test_single_require_result.js"
        self.compare_command_output_with_file_contents(cmd, filename)

    def test_compile_with_debug_defines(self):
        cmd = "python jsborg/jsborg.py tests/js tests/js/test_defines.js"
        filename = "tests/js/test_defines_result.js"
        self.compare_command_output_with_file_contents(cmd, filename)


