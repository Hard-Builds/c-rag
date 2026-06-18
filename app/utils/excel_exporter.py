import io
from typing import ByteString, Dict

import pandas as pd
from fastapi import HTTPException
from starlette import status


class ExcelExporter:
    @staticmethod
    def to_excel_bytes(df: pd.DataFrame) -> ByteString:
        try:
            # getting max width for every column
            column_width_map: Dict[str, int] = {}
            for column in df.columns:
                max_width = max(map(lambda x: len(str(x)), df[column]))
                max_width = max(max_width, len(str(column)))
                if max_width % 5 != 0:
                    max_width += 5 - (max_width % 5)
                max_width = min(max_width, 100)
                column_width_map[column] = max_width

            # Updating format for float columns
            for column in df.select_dtypes(include=["float"]):
                df[column] = df[column].map(
                    lambda x: round(x, 2) if pd.notnull(x) else x
                )

            output = io.BytesIO()
            with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
                sheet_name = "Sheet1"
                df.to_excel(
                    writer, sheet_name=sheet_name, index=False, header=False, startrow=1
                )

                workbook = writer.book
                worksheet = writer.sheets[sheet_name]

                # header format
                header_format = workbook.add_format(
                    {
                        "bold": True,
                        "text_wrap": True,
                        "valign": "vcenter",
                        "align": "center",
                        "border": True,
                    }
                )

                # Manually write headers with header format
                for col_num, col_name in enumerate(df.columns):
                    worksheet.write(0, col_num, col_name, header_format)

                # Apply cell formatting to the DataFrame cells
                cell_format = workbook.add_format({"border": True, "text_wrap": True})
                for row in range(df.shape[0]):
                    for col in range(df.shape[1]):
                        worksheet.write(row + 1, col, df.iat[row, col], cell_format)

                # Setting column width
                for idx, width in enumerate(column_width_map.values()):
                    worksheet.set_column(idx, idx, width)

            file_blob = output.getvalue()
            return file_blob
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error generating excel file: {str(e)}",
            )
