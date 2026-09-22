import pandas as pd

def load_dataset(file_path):

    df=pd.read_csv(file_path)

    df["date"] = pd.to_datetime(df["date"])

    return df


def profile_business_data(df):

    profile = {
        "rows": df.shape[0],
        "columns": df.shape[1],
        "missing_values": df.isna().sum().to_dict(),
        "duplicate_rows": int(df.duplicated().sum()),
        "data_types": df.dtypes.astype(str).to_dict(),
        "numerical_columns": df.select_dtypes(
            include="number"
        ).columns.tolist(),
        "categorical_columns": df.select_dtypes(
            include="object"
        ).columns.tolist()
    }

    return profile

    


if __name__=="__main__":

    file_path=r"N:\BizScopeAI\dataset\sales_dataset.csv"

    df=load_dataset(file_path)


    print(df.head())

    profile = profile_business_data(df)

    print("\nDataset Profile:")
    print(profile)
    