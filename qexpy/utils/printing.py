"""Utility methods for generating the string representation of value-error pairs"""

import math as m

from typing import Callable
from qexpy.settings import PrintStyle, SigFigMode

import qexpy.settings as sts


def get_printer(print_style: PrintStyle = None) -> Callable[[float, float], str]:
    """Gets the printer for the given print style

    If the print style is not specified, the global setting will be used.

    Args:
        print_style (PrintStyle): The desired print style.

    Returns:
        A printer function that takes two numbers as inputs for value and uncertainty and
        returns the string representation of the value-error pair

    """
    if not print_style:
        print_style = sts.get_settings().print_style
    if print_style == PrintStyle.SCIENTIFIC:
        return __scientific_printer
    if print_style == PrintStyle.LATEX:
        return __latex_printer
    return __default_printer


def __default_printer(value: float, error: float, latex=False) -> str:
    """Prints out the value and uncertainty in its default format"""

    pm = r"\pm" if latex else "+/-"

    if value == 0 and error == 0:
        return "0 {} 0".format(pm)
    if m.isinf(value):
        return "inf {} inf".format(pm)

    # Round the values based on significant digits
    rounded_value, rounded_error = __round_values_to_sig_figs(value, error)

    # Check if the number of decimals matches the requirement of significant figures
    decimals = __find_number_of_decimals(rounded_value, rounded_error)

    # Construct the string to return
    value_string = "{:.{num}f}".format(rounded_value, num=decimals)
    error_string = "{:.{num}f}".format(rounded_error, num=decimals) if error != 0 else "0"
    return "{} {} {}".format(value_string, pm, error_string)


def __latex_printer(value: float, error: float) -> str:
    """Prints out the value and uncertainty in latex format"""
    return __scientific_printer(value, error, latex=True)


def __scientific_printer(value: float, error: float, latex=False) -> str:
    """Prints out the value and uncertainty in scientific notation"""

    pm = r"\pm" if latex else "+/-"

    if value == 0 and error == 0:
        return "0 {} 0".format(pm)
    if m.isinf(value):
        return "inf {} inf".format(pm)

    # Find order of magnitude
    order = m.floor(m.log10(abs(value)))
    if order == 0:
        return __default_printer(value, error, latex)

    # Round the values based on significant digits
    rounded_value, rounded_error = __round_values_to_sig_figs(value, error)

    # Convert to scientific notation
    converted_value = rounded_value / (10 ** order)
    converted_error = rounded_error / (10 ** order)

    # Check if the number of decimals matches the requirement of significant figures
    decimals = __find_number_of_decimals(converted_value, converted_error)

    # Construct the string to return
    value_string = "{:.{num}f}".format(converted_value, num=decimals)
    error_string = "{:.{num}f}".format(converted_error, num=decimals) if error != 0 else "0"
    return "({} {} {}) * 10^{}".format(value_string, pm, error_string, order)


def __round_values_to_sig_figs(value: float, error: float) -> (float, float):
    """Rounds the value and uncertainty based on sig-fig settings

    This method works by first finding the order of magnitude for the error, or the value,
    depending on the sig-fig settings, and calculates a value called back-off. For example,
    to round 12345 to 3 significant figures, log10(12345) would return 4, which is the order
    of magnitude of the number. The formula for the back-off is:

    back-off = order_of_magnitude - significant_digits + 1.

    In this case, the back-off would 4 - 3 + 1 = 2. With the back-off, we first divide 12345
    by 10^2, which results in 123.45, then round it to 123, before multiplying the back-off,
    which produces 12300

    Args:
        value (float): the value of the quantity to be rounded
        error (float): the uncertainty to be rounded

    Returns:
        the rounded results for this pair

    """

    sig_fig_mode = sts.get_settings().sig_fig_mode
    sig_fig_value = sts.get_settings().sig_fig_value

    def is_valid(number):
        return not m.isinf(number) and not m.isnan(number) and number != 0

    # Check any of the inputs are invalid for the following calculations
    if sig_fig_mode in [SigFigMode.AUTOMATIC, SigFigMode.ERROR] and not is_valid(error):
        return value, error  # do no rounding if the error is 0 or invalid
    if sig_fig_mode == SigFigMode.VALUE and not is_valid(value):
        return value, error  # do no rounding if the value is 0 or invalid

    # First find the back-off value for rounding
    if sig_fig_mode in [SigFigMode.AUTOMATIC, SigFigMode.ERROR]:
        order_of_error = m.floor(m.log10(abs(error)))
        back_off = 10 ** (order_of_error - sig_fig_value + 1)
    else:
        order_of_value = m.floor(m.log10(abs(value)))
        back_off = 10 ** (order_of_value - sig_fig_value + 1)

    # Then round the value and error to the same digit
    rounded_error = round(error / back_off) * back_off
    rounded_value = round(value / back_off) * back_off

    # Return the two rounded values
    return rounded_value, rounded_error


def __find_number_of_decimals(value: float, error: float) -> int:
    """Finds the correct number of decimal places to show for a value-error pair

    This method checks the settings for significant figures and tweaks the already rounded
    value and error to having the correct number of significant figures. For example, if the
    value of a variable is 5.001, and 3 significant figures is requested. After rounding, the
    value would become 5. However, if we want it to be represented as 5.00, we need to find
    the proper number of digits after the decimal.

    The implementation is similar to that of the rounding algorithm described in the method
    above. The key is to start counting significant figures from the most significant digit,
    which is calculated by finding the order of magnitude of the value.

    See Also:
        __round_values_to_sig_figs

    """

    sig_fig_mode = sts.get_settings().sig_fig_mode
    sig_fig_value = sts.get_settings().sig_fig_value

    def is_valid(number):
        return not m.isinf(number) and not m.isnan(number) and number != 0

    # Check if the current number of significant figures satisfy the settings
    if sig_fig_mode in [SigFigMode.AUTOMATIC, SigFigMode.ERROR]:
        order = m.floor(m.log10(abs(error))) if is_valid(error) else m.floor(m.log10(abs(value)))
    else:
        order = m.floor(m.log10(abs(value))) if is_valid(value) else m.floor(m.log10(abs(error)))

    number_of_decimals = - order + sig_fig_value - 1
    return number_of_decimals if number_of_decimals > 0 else 0
