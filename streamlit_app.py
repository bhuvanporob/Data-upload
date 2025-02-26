import streamlit as st
import pandas as pd
import plotly.express as px

PARAMETER_OPTIONS = [
    "AFC", "BRU", "CAL", "CHV", "CLA", "CMV", "COO", "COV", "DCV", "DEN", "H12", "H1N", "H3N", "HAV", "HBV", "HCV", "HEV", "HIV", "HLB", "HPV", "HSV", "IAB", "LTS", "MAL", "MBL", "MGM", "MIS", "MMY", "MTB", "MTI", "MTR", "MTU", "NGC", "RBS", "STY", "TPC", "TYP"
]

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

def main():
    st.title("CSV File Uploader and Viewer")
    
    uploaded_files = st.file_uploader("Upload CSV files", type=["csv"], accept_multiple_files=True)
    
    if uploaded_files:
        combined_df = pd.DataFrame()
        for uploaded_file in uploaded_files:
            df = pd.read_csv(uploaded_file, parse_dates=['Test_date_time'])
            df = clean_data(df)
            df["Source File"] = uploaded_file.name  # Add source file name column
            combined_df = pd.concat([combined_df, df], ignore_index=True)

        # Sidebar filters
        st.sidebar.header("Filters")
        start_date = st.sidebar.date_input("Start Date", combined_df["Test_date_time"].min())
        end_date = st.sidebar.date_input("End Date", combined_df["Test_date_time"].max())
        selected_parameters = st.sidebar.multiselect("Select Parameters", PARAMETER_OPTIONS)

        # Apply filters
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
        
        tabs = st.tabs(["Lot Performance", "Chip series", "Lot Chip series", "Lot chip batch chip series", "Detailed Data"])
        
        for i, (tab, key) in enumerate(zip(tabs, index_columns.keys())):
            with tab:
                if key in index_columns:
                    pivot = filtered_df.pivot_table(index=index_columns[key], values='Patient_id', columns='Test_status', aggfunc='count', margins=True)
                    pivotdf = pd.DataFrame(pivot.to_records())
                    
                    columns_to_fill = ['Error-1', 'Error-1A', 'Error-2', 'Error-3', 'Error-4', 'Error-5', 'Invalid', 'Valid', 'All']
                    available_columns = set(pivotdf.columns) & set(columns_to_fill)
                    pivotdf[list(available_columns)] = pivotdf[list(available_columns)].fillna(0)
                    
                    if "Invalid" in pivotdf.columns and "All" in pivotdf.columns:
                        pivotdf["INV_per"] = round(pivotdf["Invalid"] / pivotdf["All"] * 100, 2)
                    else:
                        pivotdf["INV_per"] = 0
                    
                    st.dataframe(pivotdf)
                    pivotdf = pivotdf[pivotdf[index_columns[key][0]] != 'All']  # Remove rows where index is 'All'
                    
                    
                    # Interactive graphs for each index column
                    for index in index_columns[key]:
                        if index in pivotdf.columns and "INV_per" in pivotdf.columns:
                            avg_inv_per = pivotdf.groupby(index)["INV_per"].mean().reset_index()
                            fig = px.bar(avg_inv_per, x=index, y="INV_per", title=f"AVG INV_per Analysis - {key} ({index})")
                            st.plotly_chart(fig)
                else:
                    st.dataframe(filtered_df)
        
if __name__ == "__main__":
    main()
