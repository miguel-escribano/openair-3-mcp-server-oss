# MANIFEST: {"name": "time_prop", "description": "Time series stacked bar chart showing proportional contributions of categories over time.", "input_type": "wind_series", "output_type": "image", "timeout": 60}
if (!requireNamespace("jsonlite", quietly = TRUE)) stop("jsonlite required")
if (!requireNamespace("openair", quietly = TRUE)) stop("openair required")
source(file.path(Sys.getenv("OPENAIR_R_LIB", unset = "r/common"), "series_df.R"))

raw <- paste(readLines(file("stdin"), warn = FALSE), collapse = "")
payload <- jsonlite::fromJSON(raw, simplifyVector = FALSE)

artifacts_dir <- Sys.getenv("OPENAIR_ARTIFACTS_DIR", unset = "artifacts")
dir.create(artifacts_dir, recursive = TRUE, showWarnings = FALSE)

if (is.null(payload$series) || length(payload$series) == 0) stop("series required")

built <- openair_build_wind_df(payload)
df <- built$df
pollutants <- built$pollutants
payload <- built$payload
if (length(pollutants) == 0) stop("series required")
plot_title <- openair_plot_title(payload)
summary_labs <- openair_summary_labels(payload)

outfile <- file.path(artifacts_dir, paste0("time_prop_", format(Sys.time(), "%Y%m%d_%H%M%S"), ".png"))

grDevices::png(outfile, width = 1200, height = 600, res = 120)
openair::timeProp(df, pollutant = pollutants[1], proportion = "wd", main = plot_title)
invisible(grDevices::dev.off())

cat(jsonlite::toJSON(list(
  artifact = normalizePath(outfile, winslash = "/", mustWork = FALSE),
  type = "png",
  summary = paste0("Proportional time series for ", summary_labs[1]),
  tool = "time_prop"
), auto_unbox = TRUE))
