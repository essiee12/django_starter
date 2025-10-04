from rest_framework import pagination


class CustomPagination(pagination.PageNumberPagination):
    """
    Custom Global Paginator. Use ?page_size={int}
    which is the number of desired objects in a page.
    Use ?page={int} for page pagination.
    """

    page_size = 10
    page_query_param = "page"

    def paginate_queryset(self, queryset, request, view=None):
        """
        Paginate a queryset if required, either returning a
        page object, or `None` if pagination is not configured for this view.
        """
        # Get the page size from the request parameter
        page_size = request.query_params.get("page_size", self.page_size)

        try:
            self.page_size = int(page_size)
        except ValueError:
            self.page_size = self.page_size

        # Call the parent's paginate_queryset() method to get the paginated queryset
        paginated_queryset = super().paginate_queryset(queryset, request, view=view)

        # Return the paginated queryset
        return paginated_queryset
