"""
Alliance Auth Middleware
"""

from user_agents import parse


class DeviceDetectionMiddleware:
    """
    Middleware to detect the type of device making the request.
    Sets flags on the request object for easy access in views and templates.

    Flags include:
    - is_mobile: True if the device is a mobile phone.
    - is_tablet: True if the device is a tablet.
    - is_mobile_device: True if the device is either a mobile phone or a tablet.
    - is_touch_capable: True if the device has touch capabilities.
    - is_pc: True if the device is a desktop or laptop computer.
    - is_bot: True if the device is identified as a bot or crawler.
    """

    def __init__(self, get_response):
        """
        Initialize the middleware with the get_response callable.

        :param get_response:
        :type get_response:
        """

        self.get_response = get_response

    def __call__(self, request):
        """
        Process the incoming request to determine if it's from a mobile device.

        This method is called when the middleware is invoked. It inspects the
        `user-agent` header of the incoming HTTP request to determine the type
        of client making the request (e.g., mobile, tablet, PC, bot, etc.).
        Flags are set on the `request` object to indicate the client type.

        :param request: The HTTP request object.
        :type request: HttpRequest
        :return: The HTTP response object after processing the request.
        :rtype: HttpResponse
        """

        # Retrieve the user-agent string from the request headers
        user_agent_string = request.headers.get("user-agent", "")

        # Parse the user-agent string to extract client information
        user_agent = parse(user_agent_string)

        # Set flags on the request object based on the client type
        request.is_mobile = user_agent.is_mobile  # True if the client is a mobile phone
        request.is_tablet = user_agent.is_tablet  # True if the client is a tablet
        request.is_mobile_device = user_agent.is_mobile or user_agent.is_tablet  # True if mobile phone or tablet
        request.is_touch_capable = user_agent.is_touch_capable  # True if the client supports touch input
        request.is_pc = user_agent.is_pc  # True if the client is a PC
        request.is_bot = user_agent.is_bot  # True if the client is a bot

        # Pass the request to the next middleware or view and get the response
        response = self.get_response(request)

        # Return the processed response
        return response
