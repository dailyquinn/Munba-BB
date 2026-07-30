from django.dispatch import Signal

"""
Basic signal sent after an ESI requests
    from django.dispatch import receiver
    from esi.signals import esi_request_statistics

    @receiver(esi_request_statistics)
    def esi_callback(sender, operation, status_code, headers, latency, bucket, **kwargs):
        # do stuff
        pass
"""
esi_request_statistics = Signal(
    # providing_args=[
    #     "operation",
    #     "status_code",
    #     "headers",
    #     "latency",
    #     "bucket"
    # ]
)
