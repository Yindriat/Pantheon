CREATE TABLE IF NOT EXISTS pantheon (
    en_curid INT,
    name TEXT,
    numlangs INT,
    birthcity TEXT,
    birthstate TEXT,
    countryName TEXT,
    countryCode TEXT,
    countryCode3 TEXT,
    LAT REAL,
    LON REAL,
    continentName TEXT,
    birthyear TEXT,
    gender TEXT,
    occupation TEXT,
    industry TEXT,
    domain TEXT,
    TotalPageViews BIGINT,
    L_star REAL,
    StdDevPageViews REAL,
    PageViewsEnglish BIGINT,
    PageViewsNonEnglish BIGINT,
    AverageViews REAL,
    HPI REAL,
    ranking INT PRIMARY KEY
);

-- Copy data from the CSV file (converted from pantheon.xlsx by convert_xlsx.py)
COPY pantheon FROM '/tmp/pantheon.csv' WITH (FORMAT csv, HEADER);
