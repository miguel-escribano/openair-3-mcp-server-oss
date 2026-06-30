# MANIFEST: {"name": "import_traj", "description": "Import pre-calculated HYSPLIT 96-hour back trajectories from the openair trajectory database. Returns TrajSeriesV1-compatible JSON.", "input_type": "import_params", "output_type": "series", "timeout": 120}
if (!requireNamespace("jsonlite", quietly = TRUE)) stop("jsonlite required")
if (!requireNamespace("openair", quietly = TRUE)) stop("openair required")

raw <- paste(readLines(file("stdin"), warn = FALSE), collapse = "")
payload <- jsonlite::fromJSON(raw, simplifyVector = FALSE)

site <- payload$site
if (is.null(site)) stop("site required (e.g. 'London')")
start_date <- payload$start_date
end_date <- payload$end_date
if (is.null(start_date) || is.null(end_date)) stop("start_date and end_date required (YYYY-MM-DD)")

year_start <- as.integer(format(as.Date(start_date), "%Y"))
year_end <- as.integer(format(as.Date(end_date), "%Y"))
years <- seq(year_start, year_end)

traj <- openair::importTraj(site = site, year = years)
if (is.null(traj) || nrow(traj) == 0) stop(paste0("No trajectory data found for site='", site, "'"))

out <- list(
  date = format(traj$date, "%Y-%m-%dT%H:%M:%SZ"),
  lat = traj$lat,
  lon = traj$lon,
  height = traj$height,
  pressure = if ("pressure" %in% names(traj)) traj$pressure else rep(NA_real_, nrow(traj)),
  hour_inc = traj$hour.inc,
  traj_id = if ("traj_id" %in% names(traj)) traj$traj_id else NULL,
  meta = list(source = "openair_importTraj", site = site)
)
cat(jsonlite::toJSON(out, auto_unbox = TRUE, na = "null"))
