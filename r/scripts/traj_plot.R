# MANIFEST: {"name": "traj_plot", "description": "Back-trajectory line plot. Visualises air mass origins. Input: TrajSeriesV1 (from import_traj).", "input_type": "traj_series", "output_type": "image", "timeout": 120}
if (!requireNamespace("jsonlite", quietly = TRUE)) stop("jsonlite required")
if (!requireNamespace("openair", quietly = TRUE)) stop("openair required")

raw <- paste(readLines(file("stdin"), warn = FALSE), collapse = "")
payload <- jsonlite::fromJSON(raw, simplifyVector = FALSE)

artifacts_dir <- Sys.getenv("OPENAIR_ARTIFACTS_DIR", unset = "artifacts")
dir.create(artifacts_dir, recursive = TRUE, showWarnings = FALSE)

if (is.null(payload$date) || is.null(payload$lat) || is.null(payload$lon)) {
  stop("date, lat, lon required (TrajSeriesV1 format)")
}

df <- data.frame(
  date = as.POSIXct(unlist(payload$date), format = "%Y-%m-%dT%H:%M:%OSZ", tz = "UTC"),
  lat = as.numeric(unlist(payload$lat)),
  lon = as.numeric(unlist(payload$lon)),
  height = as.numeric(unlist(payload$height)),
  hour.inc = as.integer(unlist(payload$hour_inc)),
  stringsAsFactors = FALSE
)

outfile <- file.path(artifacts_dir, paste0("traj_plot_", format(Sys.time(), "%Y%m%d_%H%M%S"), ".png"))

grDevices::png(outfile, width = 1200, height = 900, res = 120)
openair::trajPlot(df)
invisible(grDevices::dev.off())

cat(jsonlite::toJSON(list(
  artifact = normalizePath(outfile, winslash = "/", mustWork = FALSE),
  type = "png",
  summary = "Back-trajectory plot",
  tool = "traj_plot"
), auto_unbox = TRUE))
