# MANIFEST: {"name": "import_europe", "description": "Import air quality data from European monitoring networks via openair. Returns SeriesV1-compatible JSON. Note: data available until Feb 2024.", "input_type": "import_params", "output_type": "series", "timeout": 180}
if (!requireNamespace("jsonlite", quietly = TRUE)) stop("jsonlite required")
if (!requireNamespace("openair", quietly = TRUE)) stop("openair required")
source(file.path(Sys.getenv("OPENAIR_R_LIB", unset = "r/common"), "series_df.R"))

raw <- paste(readLines(file("stdin"), warn = FALSE), collapse = "")
payload <- jsonlite::fromJSON(raw, simplifyVector = FALSE)

site <- payload$site
if (is.null(site)) stop("site required (European station code)")
start_date <- payload$start_date
end_date <- payload$end_date
if (is.null(start_date) || is.null(end_date)) stop("start_date and end_date required (YYYY-MM-DD)")

year_start <- as.integer(format(as.Date(start_date), "%Y"))
year_end <- as.integer(format(as.Date(end_date), "%Y"))
years <- seq(year_start, year_end)

data <- openair::importEurope(site = site, year = years)
if (is.null(data) || nrow(data) == 0) stop(paste0("No European data returned for site='", site, "'"))

dates <- as.POSIXct(data$date, tz = "UTC")
mask <- dates >= as.POSIXct(start_date, tz = "UTC") & dates <= as.POSIXct(paste0(end_date, " 23:59:59"), tz = "UTC")
data <- data[mask, ]

site_label <- if ("site" %in% names(data)) {
  as.character(data$site[!is.na(data$site)][1])
} else {
  as.character(site)[1]
}

out <- openair_df_to_seriesv1(data, meta = list(source = "europe", site = site_label))
cat(jsonlite::toJSON(out, auto_unbox = TRUE, na = "null"))
