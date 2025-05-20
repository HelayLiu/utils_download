import glob
import os
import sys
import re
import solcx
from semantic_version import Version
import solidity_parser
AVAILABLE_SOLC_VERSION_PATHS = {}

class SolcVersionUnavailableException(Exception):
    def __init__(self, solc_version):
        self.solc_version = solc_version
    
    def __str__(self):
        return 'solc %s not available' % self.solc_version


class ParseException(Exception):
    def __init__(self, reason):
        self.reason = reason
    
    def __str__(self):
        return self.reason

# Parse out solc version, e.g. v0.4.19, from
# the version string returned by etherscan.io
def parse_solc_version_string(solc_version_string):
    # Pattern 1: v0.4.24-nightly.2018.5.10+commit.85d417a8
    # Pattern 2: v0.4.23+commit.124ca40d
    # Patters 3: vyper:0.1.0b11

    # We don't support Vyper contracts at the moment
    if solc_version_string.startswith('vyper:'):
        return 'vyper'
    
    separator_pos = solc_version_string.find('-')
    if separator_pos == -1:
        separator_pos = solc_version_string.find('+')
        if separator_pos == -1:
            return None
    solc_version = solc_version_string[:separator_pos]

    # Sanity checks
    len_solc_version = len(solc_version)
    if len_solc_version < 6 or len_solc_version > 7:
        return None
    if solc_version[0] != 'v':
        return None
    if solc_version.find('.') != 2:
        return None
    
    return solc_version


def get_available_solc_versions():
    global AVAILABLE_SOLC_VERSIONS

    # solc versions installed by py-solc
    py_solc_path = os.path.expanduser('~/.py-solc')
    if os.path.isdir(py_solc_path):
        py_solc_version_regex = os.path.join(py_solc_path, '*/bin/solc')
        for solc_path in glob.glob(py_solc_version_regex):
            solc_version = solc_path.split('/')[-3].replace('solc-', '')
            AVAILABLE_SOLC_VERSION_PATHS[solc_version] = os.path.join(solc_path, 'solc')

    # solc versions installed by py-solc-x
    solcx_path = os.path.expanduser('~/.solcx')
    if os.path.isdir(solcx_path):
        py_solcx_version_regex = os.path.join(solcx_path, 'solc-v*')
        for solc_path in glob.glob(py_solcx_version_regex):
            solc_version = solc_path.split('/')[-1].replace('solc-v', '')
            AVAILABLE_SOLC_VERSION_PATHS[solc_version] = solc_path
    
    # solc versions installed by solc-select (shell script version)
    solc_select_path = os.path.expanduser('~/.solc-select')
    if os.path.isdir(solc_select_path):
        solc_select_version_regex = os.path.join(solc_select_path, 'usr/bin/solc-v*')
        for solc_path in glob.glob(solc_select_version_regex):
            solc_version = solc_path.split('/')[-1].replace('solc-', '')
            AVAILABLE_SOLC_VERSION_PATHS[solc_version] = solc_path

    # solc versions installed by solc-select (pip version)
    solc_select_path = os.path.expanduser('~/.solc-select/artifacts')
    if os.path.isdir(solc_select_path):
        solc_select_version_regex = os.path.join(solc_select_path, 'solc-*')
        for solc_path in glob.glob(solc_select_version_regex):
            # print(solc_path)
            solc_version = solc_path.split('/')[-1].replace('solc-', '')
            solc_path = os.path.join(solc_path, solc_path.split('/')[-1])
            AVAILABLE_SOLC_VERSION_PATHS[solc_version] = solc_path
    
    AVAILABLE_SOLC_VERSIONS = list(AVAILABLE_SOLC_VERSION_PATHS.keys())
    # Sort from latest to oldest. Sorting is required
    # to determine the highest possible solc version
    # a contract can be compiled with
    AVAILABLE_SOLC_VERSIONS.sort(reverse=True, key=lambda v: (Version(v).major, Version(v).minor, Version(v).patch))


def get_solc_path_from_version(solc_version, log=None, lookup_if_unavailable=False):
    get_available_solc_versions()
    try:
        solc_path = AVAILABLE_SOLC_VERSION_PATHS[solc_version]
        if log:
            print('solc %s found at %s' % (solc_version, solc_path))
        return solc_path
    except KeyError:
        if lookup_if_unavailable:
            if log:
                log.warn('solc %s unavailable, finding latest available patch version instead' % solc_version)
            try:
                solc_version = get_latest_patch_version(solc_version)
                solc_version = str(solc_version)
                print('solc %s found as an alternative' % solc_version)
                solc_path = AVAILABLE_SOLC_VERSION_PATHS[solc_version]
                print('solc %s found at %s' % (solc_version, solc_path))
                return solc_path
            except SolcVersionUnavailableException:
                if log:
                    print('No suitable patch version found')
                raise SolcVersionUnavailableException(solc_version)
        else:
            if log:
                print('solc %s unavailable' % solc_version)
            raise SolcVersionUnavailableException(solc_version)
        
def get_latest_patch_version(version_string):
    # Pre-pend a 'v' if not present.
    # Required because the version string is used
    # as a needle in the list of available solc versions
    # if not version_string.startswith('v'):
    #     version_string = 'v%s' % version_string
    if version_string.startswith('v'):
        version_string = version_string[1:]
    available_solc_version_strings = AVAILABLE_SOLC_VERSIONS            # Sorted from latest to oldest
    given_solc_version = Version(version_string)

    # Iterate over the remaining higher solc versions, starting from the given version
    for available_solc_version_string in AVAILABLE_SOLC_VERSIONS:
        available_solc_version = Version(available_solc_version_string)
        if available_solc_version.major == given_solc_version.major \
                and available_solc_version.minor == given_solc_version.minor \
                    and available_solc_version.patch >= given_solc_version.patch:
            return available_solc_version
    
    raise SolcVersionUnavailableException(version_string)


# Given a solc version string, get the previous solc
# version. This functionality is required to satisfy
# < and > version constraints.
def get_previous_solc_version(version_string):
    available_solc_version_strings = AVAILABLE_SOLC_VERSIONS            # Sorted from latest to oldest
    given_solc_version = Version(version_string)

    for available_solc_version_string in available_solc_version_strings:
        available_solc_version = Version(available_solc_version_string)
        if available_solc_version < given_solc_version:
            break
    
    return available_solc_version


# Given a solc version string, get the next solc
# version. This functionality is required to satisfy
# < and > version constraints.
def get_next_solc_version(version_string):
    available_solc_version_strings = AVAILABLE_SOLC_VERSIONS            # Sorted from latest to oldest
    given_solc_version = Version(version_string)

    available_solc_version_strings = reversed(available_solc_version_strings)
    for available_solc_version_string in available_solc_version_strings:
        available_solc_version = Version(available_solc_version_string)
        if available_solc_version > given_solc_version:
            break
    
    return available_solc_version


# Given a Solidity source file, enumerate all the
# soidity version pragma directives, and pick the
# latest version that can compile this contract file.
# Install the required solc version, if not already
# installed. Return the path to the solc binary.
def get_solc_path(contract_path, log=None):
    # Enumerate solc versions installed on the system
    get_available_solc_versions()

    contract_name = os.path.basename(contract_path)
    try:
        source_unit = solidity_parser.parser.parse_file(contract_path)
        source_unit_object = solidity_parser.parser.objectify(source_unit)
        pragmas = source_unit_object.pragmas
        solidity_pragmas = list(filter(lambda x: x.name == 'solidity', pragmas))
        version_strings = list(map(lambda x: x.value, solidity_pragmas))

        if len(solidity_pragmas) == 0:
               print('pragma not found, returning highest available solc version: %s' % contract_name)
    except Exception as e:
        # python-solidity-parser (https://github.com/ConsenSys/python-solidity-parser) fails to parse
        # well-formed contracts like `BanCOREFarming.sol`. Here's a dirty fix that manually tokenizes
        # the contract lines, extract the pragmas, and the respective version constraints
        with open(contract_path, 'r') as fp:
            lines = fp.readlines()
        version_strings = []
        for line in lines:
            tokens = line.strip().split()
            if len(tokens) > 2:
                if tokens[0] == 'pragma' and tokens[1] == 'solidity':
                    version_strings.append(''.join(tokens[2:]))
        # We raise the original exception if the hack fails
        if len(version_strings) == 0:
            raise ParseException(str(e))
    
    # Solve version constraints
    # The only generic way I can think of is using a constraint solver
    # For now, we compute the highest solc version that can compile this source
    available_solc_version_strings = AVAILABLE_SOLC_VERSIONS            # Sorted from latest to oldest
    maximum_min_version = Version(available_solc_version_strings[-1])
    minimum_max_version = Version(available_solc_version_strings[0])

    # Update min and max solc versions
    def update_min_max_versions(version_string, update_maximum_min=False, update_minimum_max=False):
        nonlocal maximum_min_version
        nonlocal minimum_max_version
        if isinstance(version_string, str):
            if version_string.startswith('v'):
                version_string = version_string[1:]
            version = Version(version_string)
        else:
            version = version_string
        # Update min solc version
        if update_maximum_min:
            if version > maximum_min_version:
                maximum_min_version = version
        
        # Update max solc version
        if update_minimum_max:
            if version < minimum_max_version:
                minimum_max_version = version
    
    # Break compound constraints to individual simpler ones
    # e.g. pragma solidity >=0.4.24 <0.6.0;
    # solidity_parser parses it to '>=0.4.24<0.6.0' (no space)
    simple_version_strings = []
    version_pattern = '[<>=\^]*\d\.\d\.\d{1,2}'
    for version_string in version_strings:
        versions = re.findall(version_pattern, version_string)
        simple_version_strings.extend(versions)
    if log:
        print('Version constraints: %s' % str(simple_version_strings))

    # Iterate over all version constraints
    for version_string in simple_version_strings:
        # There could be the following version constraints:
        # ^, =, <, >, <=, >=
        # Match longer symbols (>=, <=) before the shorter ('>', '<') ones
        
        if version_string[:1] == '0':
            numeric_version_string = 'v' + version_string
            update_min_max_versions(numeric_version_string, True, True)

        # ^ imposes both lower and upper limits
        elif version_string[:1] == '^':
            min_version_string = 'v' + version_string[1:]
            max_version_string = get_latest_patch_version(min_version_string)
            update_min_max_versions(min_version_string, True, False)
            update_min_max_versions(max_version_string, False, True)
        
        # >= imposes a lower limit
        elif version_string[:2] == '>=':
            min_version_string = 'v' + version_string[2:]
            update_min_max_versions(min_version_string, True, False)

        # <= imposes an upper limit
        elif version_string[:2] == '<=':
            max_version_string = 'v' + version_string[2:]
            update_min_max_versions(max_version_string, False, True)
        
        # > imposes a lower limit
        elif version_string[:1] == '>':
            min_version_string = get_next_solc_version(version_string[1:])
            update_min_max_versions(min_version_string, True, False)

        # < imposes an upper limit
        elif version_string[:1] == '<':
            max_version_string = get_previous_solc_version(version_string[1:])
            update_min_max_versions(max_version_string, False, True)
        
        # = imposes an exact limit
        elif version_string[:1] == '=':
            exact_version_string = 'v' + version_string[1:]
            update_min_max_versions(exact_version_string, True, True)
            break   # This is a hard constraint
        
        # Unknown version constraint
        else:
            if log:
                print('Unknown version constraint: %s' % version_string)
            sys.exit(1)
    
    # At this point, any solc version between maximum_min_version_string
    # and minimum_max_version_string should be able to compile this source.
    solc_version = str(maximum_min_version)
    if log:
        print('solc version: %s' % solc_version)

    # Get solc binary path that can compile this contract
    solc_binary = 'solc-' + solc_version

    # Get installed solc versions
    installed_solc_versions = list(AVAILABLE_SOLC_VERSION_PATHS.keys())

    # Is the required solc version already installed?
    # Install otherwise
    if solc_version not in installed_solc_versions:
        try:
            solcx.install_solc(solc_version)
        except Exception as e:
            print(e)
            sys.exit(1)
    
    # Form required the path pointing to the required solc binary
    solc_path = AVAILABLE_SOLC_VERSION_PATHS[solc_version]
    return solc_version, solc_path
