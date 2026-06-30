# MANIFEST: {"name": "import_ukaq", "description": "Import data from UK Air Pollution Networks (AQE, SAQN, WAQN, NI, local). Returns SeriesV1-compatible JSON.", "input_type": "import_params", "output_type": "series", "timeout": 120}
if (!requireNamespace("jsonlite", quietly = TRUE)) stop("jsonlite required")
if (!requireNamespace("openair", quietly = TRUE)) stop("openair required")
source(file.path(Sys.getenv("OPENAIR_R_LIB", unset = "r/common"), "series_df.R"))

raw <- paste(readLines(file("stdin"), warn = FALSE), collapse = "")
payload <- jsonlite::fromJSON(raw, simplifyVector = FALSE)

site <- payload$site
if (is.null(site)) stop("site required")
start_date <- payload$start_date
end_date <- payload$end_date
if (is.null(start_date) || is.null(end_date)) stop("start_date and end_date required (YYYY-MM-DD)")

network <- if (!is.null(payload$network)) payload$network else "aqe"
year_start <- as.integer(format(as.Date(start_date), "%Y"))
year_end <- as.integer(format(as.Date(end_date), "%Y"))
years <- seq(year_start, year_end)

pollutant_arg <- if (!is.null(payload$pollutants) && length(payload$pollutants) > 0) {
  unlist(payload$pollutants)
} else {
  "all"
}

data <- openair::importUKAQ(
  site = site,
  year = years,
  network = network,
  pollutant = pollutant_arg,
  meta = TRUE
)
if (is.null(data) || nrow(data) == 0) stop(paste0("No data returned for site='", site, "' network='", network, "'"))

dates <- as.POSIXct(data$date, tz = "UTC")
mask <- dates >= as.POSIXct(start_date, tz = "UTC") & dates <= as.POSIXct(paste0(end_date, " 23:59:59"), tz = "UTC")
data <- data[mask, ]

site_label <- if ("site" %in% names(data)) {
  as.character(data$site[!is.na(data$site)][1])
} else {
  as.character(site)[1]
}

out <- openair_df_to_seriesv1(data, meta = list(source = network, site = site_label))
cat(jsonlite::toJSON(out, auto_unbox = TRUE, na = "null"))
