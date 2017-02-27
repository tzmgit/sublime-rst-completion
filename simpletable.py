# -*- coding: utf-8 -*-

import re
try:
    from .helpers import BaseBlockCommand
except ValueError:
    from helpers import BaseBlockCommand


class SimpletableCommand(BaseBlockCommand):

    _SEPARATOR = '  '

    def get_result(self, indent, table):
        result = '\n'.join(self._draw_table(indent, table))
        result += '\n'
        return result

    def run(self, edit):
        region, lines, indent = self.get_block_bounds()
        table = self._parse_table(lines)
        result = self.get_result(indent, table)
        self.view.replace(edit, region, result)

    def _split_table_cells(self, row_string):
        return re.split(r'\s\s+', row_string.strip())

    def _parse_table(self, raw_lines):
        parsed_lines = []
        for row_string in raw_lines:
            if not self._row_is_separator(row_string):
                parsed_lines.append(self._split_table_cells(row_string))
        return parsed_lines

    def _row_is_separator(self, row):
        return re.match('^[\t =]+$', row)

    def _table_header_line(self, widths):
        linechar = '='
        parts = []
        for width in widths:
            parts.append(linechar * width)
        return SimpletableCommand._SEPARATOR.join(parts)

    def _get_column_max_widths(self, table):
        widths = []
        for row in table:
            num_fields = len(row)
            # dynamically grow
            if num_fields >= len(widths):
                widths.extend([0] * (num_fields - len(widths)))
            for i in range(num_fields):
                field_width = len(row[i])
                widths[i] = max(widths[i], field_width)
        return widths

    def _pad_fields(self, row, width_formats):
        """ Pad all fields using width formats """
        new_row = []
        for i in range(len(row)):
            col = row[i]
            col = width_formats[i] % col
            new_row.append(col)
        return new_row

    def _draw_table(self, indent, table):
        if not table:
            return []

        for_item = None
        vars_in_for = []
        insert_empty_cell = False
        start_mult_line_for = False
        for idx, row in enumerate(table):
            if idx > 0:
                pre_row = table[idx - 1]
                if len(row) <= 1:
                    continue
                if row[1].upper() == ':FOR':
                    for_item = row[2]
                    vars_in_for = []
                    continue
                if for_item:
                    if (len(row) > 1 and (row[0] not in ['\\', '#\\'])) or pre_row[0] != '\\':  # new keyword start
                        for_item = None
                        vars_in_for = []
                        continue
                if insert_empty_cell and len(row) > 1 and row[1] == '...':
                    row.insert(1, '')
                    table[idx] = row
                    insert_empty_cell = True
                    continue
                insert_empty_cell = False
                if len(pre_row) > 1 and pre_row[1].upper() == ':FOR' and pre_row[-1].upper() != 'IN':
                    # add a empty cell as the second cell for the second line in a for loop
                    row.insert(1, '')
                    table[idx] = row
                    insert_empty_cell = True
                    start_mult_line_for = True
                elif for_item:
                    for cell in row[:]:
                        if for_item and for_item in cell:
                            row.insert(1, '')
                            table[idx] = row
                            insert_empty_cell = True
                            break
                        elif vars_in_for:
                            for var_in_for in vars_in_for:
                                if var_in_for in cell:
                                    row.insert(1, '')
                                    table[idx] = row
                                    insert_empty_cell = True
                                    break
                        if insert_empty_cell:
                            break
                if insert_empty_cell:
                    # find a var defined inside FOR loop being used in current row, so the row is inside the FOR loop
                    for t_idx, t_cell in enumerate(row):
                        if t_cell.endswith('='):
                            vars_in_for.append(t_cell[:-1])
                            if t_idx > 2:
                                for extra_var in row[2:t_idx]:
                                    vars_in_for.append(extra_var)
                            break
                if for_item and (for_item + '=') in str(row) or not insert_empty_cell:  # var is re-defined
                    for_item = None
                    vars_in_for = []

        # if the second column is a dot sign, replace it with blank string and keep this column
        for idx, row in enumerate(table):
            if len(row) > 2 and row[1] == '.':
                row[1] = ''
                table[idx] = row

        col_widths = self._get_column_max_widths(table)
        # Reserve room for separator
        len_sep = len(SimpletableCommand._SEPARATOR)
        sep_col_widths = [(col + len_sep) for col in col_widths]
        width_formats = [('%-' + str(w) + 's' + SimpletableCommand._SEPARATOR) for w in col_widths]

        header_line = self._table_header_line(sep_col_widths)
        output = [indent + header_line]
        first = True
        for row in table:
            # draw the lines (num_lines) for this row
            row = self._pad_fields(row, width_formats)
            output.append(indent + SimpletableCommand._SEPARATOR.join(row))
            # draw the under separator for header
            if first:
                output.append(indent + header_line)
                first = False

        output.append(indent + header_line)
        return output
