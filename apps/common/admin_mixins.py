"""Reusable admin mixins used across apps."""

from import_export.admin import ExportMixin
from import_export.formats import base_formats
from unfold.contrib.import_export.forms import SelectableFieldsExportForm


class CSVExportAdminMixin(ExportMixin):
    """Enable CSV export with Unfold-styled export forms."""

    export_form_class = SelectableFieldsExportForm
    formats = [base_formats.CSV]
