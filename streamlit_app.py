import streamlit as st
import pandas as pd
import plotly.express as px
from io import BytesIO
from openpyxl.styles import PatternFill, Font, Border, Side

PARAMETER_OPTIONS = [
    "AFC", "BRU", "CAL", "CHV", "CLA", "CMV", "COO", "COV", "DCV", "DEN", "H12", "H1N", "H3N", "HAV", "HBV", "HCV", "HEV", "HIV", "HLB", "HPV", "HSV", "IAB", "LTS", "MAL", "MBL", "MGM", "MIS", "MMY", "MTB", "MTI", "MTR", "MTU", "NGC", "RBS", "STY", "TPC", "TYP"
]

def apply_excel_formatting(writer, sheet_name, df):
    workbook = writer.book
    worksheet = writer.sheets[sheet_name]

    header_fill = PatternFill(start_color="4F81BD", end_color="4F81BD", fill_type="solid")
    white_fill = PatternFill(start_color="FFFFFF", end_color="FFFFFF", fill_type="solid")
    alternate_fill = PatternFill(start_color="DCE6F1", end_color="DCE6F1", fill_type="solid")
    green_fill = PatternFill(start_color="B3E7B5", end_color="B3E7B5", fill_type="solid")
    red_fill = PatternFill(start_color="FDB1B1", end_color="FDB1B1", fill_type="solid")
    green_font = Font(color="006100")
    red_font = Font(color="9C0006")

    thin_border = Border(
        left=Side(style="thin"),
        right=Side(style="thin"),
        top=Side(style="thin"),
        bottom=Side(style="thin")
    )

    for cell in worksheet[1]:
        cell.fill = header_fill
        cell.border = thin_border

    for row_idx, row in enumerate(worksheet.iter_rows(min_row=2), start=2):
        fill = white_fill if row_idx % 2 == 0 else alternate_fill
        for cell in row:
            cell.fill = fill
            cell.border = thin_border

    inv_col_idx = None
    for col_idx, cell in enumerate(worksheet[1], start=1):
        if cell.value == "INV_per":
            inv_col_idx = col_idx
            break

    if inv_col_idx:
        for row_idx, value in enumerate(df["INV_per"], start=2):
            cell = worksheet.cell(row=row_idx, column=inv_col_idx)
            if isinstance(value, (int, float)):
                if value > 7:
                    cell.fill = red_fill
                    cell.font = red_font
                else:
                    cell.fill = green_fill
                    cell.font = green_font
            cell.border = thin_border

def clean_data(df):
    df = df[df['Test_status'].notnull()]
    df_wun = df[~df['User_name'].isin(['Service'])]
    df_wun = df_wun[~df_wun['Lab_name'].isin(['QC'])]
    df_clean = df_wun.assign(Truelab_id=df_wun['Truelab_id'].apply(lambda x: x.partition('-')[0]))
    df_clean['Chip_serial_no'] = df_clean['Chip_serial_no'].str[:2]
    df_clean = df_clean.drop_duplicates(keep='first')
    df_clean['Ct1'] = pd.to_numeric(df_clean['Ct1'], errors='coerce').fillna(0)
    df_clean['Ct2'] = pd.to_numeric(df_clean['Ct2'], errors='coerce').fillna(0)
    df_clean['Ct3'] = pd.to_numeric(df_clean['Ct3'], errors='coerce').fillna(0)
    df_clean = df_clean[~df_clean['Chip_serial_no'].str[0].str.isdigit()]
    df_clean = df_clean[df_clean['Chip_serial_no'].str[1].str.isdigit()]
    masterlist = pd.read_excel('Feb Materlist.xlsx',sheet_name='Main data')
    df_merged = pd.merge(df_clean,masterlist[['Truelab_id','Zone','Account Owner','State','Customer Type']],on='Truelab_id',how='left')  
    return df_merged

def generate_excel(dataframes):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        for sheet_name, df in dataframes.items():
            df.to_excel(writer, sheet_name=sheet_name, index=False)
            apply_excel_formatting(writer, sheet_name, df)
    output.seek(0)
    return output

def main():
    st.title("CSV File Uploader and Viewer")
    
    uploaded_files = st.file_uploader("Upload CSV files", type=["csv"], accept_multiple_files=True)
    
    if uploaded_files:
        combined_df = pd.DataFrame()
        for uploaded_file in uploaded_files:
            df = pd.read_csv(uploaded_file, parse_dates=['Test_date_time'])
            df = clean_data(df)
            df["Source File"] = uploaded_file.name
            combined_df = pd.concat([combined_df, df], ignore_index=True)

        st.sidebar.header("Filters")
        start_date = st.sidebar.date_input("Start Date", combined_df["Test_date_time"].min())
        end_date = st.sidebar.date_input("End Date", combined_df["Test_date_time"].max())
        selected_parameters = st.sidebar.multiselect("Select Parameters", PARAMETER_OPTIONS)

        filtered_df = combined_df[(combined_df['Test_date_time'] >= pd.to_datetime(start_date)) &
                                  (combined_df['Test_date_time'] <= pd.to_datetime(end_date)) &
                                  (combined_df['Profile_id'].isin(selected_parameters))]

        index_columns = {
            "Lot Performance": ['Lot'],
            "Chip series": ['Chip_serial_no'],
            "Lot Chip series": ['Lot', 'Chip_serial_no'],
            "Lot chip batch chip series": ['Lot', 'Chip_batchno', 'Chip_serial_no'],
            "Detailed Data": ['Zone','State','Account Owner','Customer Type','Lab_name', 'Truelab_id', 'Lot', 'Chip_batchno', 'Chip_serial_no']
        }
        
        dataframes = {}
        tabs = st.tabs(list(index_columns.keys()))
        
        for tab, key in zip(tabs, index_columns.keys()):
            with tab:
                pivot = filtered_df.pivot_table(index=index_columns[key], values='Patient_id', columns='Test_status', aggfunc='count', margins=True)
                pivotdf = pd.DataFrame(pivot.to_records())
                pivotdf.fillna(0, inplace=True)
                if "Invalid" in pivotdf.columns and "All" in pivotdf.columns:
                    pivotdf["INV_per"] = round(pivotdf["Invalid"] / pivotdf["All"] * 100, 2)
                dataframes[key] = pivotdf
                st.dataframe(pivotdf)

                pivotdf = pivotdf[pivotdf[index_columns[key][0]] != 'All']  # Remove rows where index is 'All'
                    
                    # Interactive graphs for each index column
                for index in index_columns[key]:
                    if index in pivotdf.columns and "INV_per" in pivotdf.columns:
                        avg_inv_per = pivotdf.groupby(index)["INV_per"].mean().reset_index()
                        fig = px.bar(avg_inv_per, x=index, y="INV_per", title=f"AVG INV_per Analysis - {key} ({index})")
                        st.plotly_chart(fig)
        
        excel_file = generate_excel(dataframes)
        st.sidebar.download_button(
            label="📥 Download Excel File",
            data=excel_file,
            file_name="data_export.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

if __name__ == "__main__":
    main()
