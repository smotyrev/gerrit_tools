ENDC = '\033[0m'


def header(text: str):
    return '\033[95m{}{}'.format(text.rstrip(ENDC), ENDC)


def ok_blue(text: str):
    return '\033[94m{}{}'.format(text.rstrip(ENDC), ENDC)


def ok_cyan(text: str):
    return '\033[96m{}{}'.format(text.rstrip(ENDC), ENDC)


def ok_green(text: str):
    return '\033[92m' + text.rstrip(ENDC) + ENDC


def warn(text: str):
    return '\033[93m' + text.rstrip(ENDC) + ENDC


def fail(text: str):
    return '\033[91m' + text.rstrip(ENDC) + ENDC


def bold(text: str):
    return '\033[1m' + text.rstrip(ENDC) + ENDC


def underline(text: str):
    return '\033[4m' + text.rstrip(ENDC) + ENDC
