# MANIFEST: {"name": "calendar_plot", "description": "Plot time series values in a calendar format. Useful for identifying day-of-week and seasonal patterns.", "input_type": "series", "output_type": "image", "timeout": 60}
if (!requireNamespace("jsonlite", quietly = TRUE)) stop("jsonlite required")
if (!requireNamespace("openair", quietly = TRUE)) stop("openair required")
source(file.path(Sys.getenv("OPENAIR_R_LIB", unset = "r/common"), "series_df.R"))

raw <- paste(readLines(file("stdin"), warn = FALSE), collapse = "")
payload <- jsonlite::fromJSON(raw, simplifyVector = FALSE)

artifacts_dir <- Sys.getenv("OPENAIR_ARTIFACTS_DIR", unset = "artifacts")
dir.create(artifacts_dir, recursive = TRUE, showWarnings = FALSE)

built <- openair_build_series_df(payload)
df <- built$df
pollutants <- built$pollutants
payload <- built$payload
pollutant <- pollutants[1]
summary_labs <- openair_summary_labels(payload)

outfile <- file.path(artifacts_dir, paste0("calendar_plot_", format(Sys.time(), "%Y%m%d_%H%M%S"), ".png"))

grDevices::png(outfile, width = 1200, height = 800, res = 120)
openair::calendarPlot(df, pollutant = pollutant, main = openair_plot_title(payload))
invisible(grDevices::dev.off())

cat(jsonlite::toJSON(list(
  artifact = normalizePath(outfile, winslash = "/", mustWork = FALSE),
  type = "png",
  summary = paste0("Calendar plot for ", summary_labs[1]),
  tool = "calendar_plot"
), auto_unbox = TRUE))
