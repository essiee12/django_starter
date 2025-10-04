from django_filters import FilterSet, DateFilter


class DateRangeFilter(FilterSet):
    """
    DateRange Filter
    """

    start_date = DateFilter(field_name="created_at", lookup_expr="gte")
    end_date = DateFilter(field_name="created_at", lookup_expr="lte")

    class Meta:
        abstract = True
