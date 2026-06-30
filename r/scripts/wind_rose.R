# MANIFEST: {"name": "wind_rose", "description": "Traditional wind rose showing frequency and speed distribution by direction. Requires ws (wind speed) and wd (wind direction) columns.", "input_type": "wind_series", "output_type": "image", "timeout": 60}
if (!requireNamespace("jsonlite", quietly = TRUE)) stop("jsonlite required")
if (!requireNamespace("openair", quietly = TRUE)) stop("openair required")
source(file.path(Sys.getenv("OPENAIR_R_LIB", unset = "r/common"), "series_df.R"))

raw <- paste(readLines(file("stdin"), warn = FALSE), collapse = "")
payload <- jsonlite::fromJSON(raw, simplifyVector = FALSE)

artifacts_dir <- Sys.getenv("OPENAIR_ARTIFACTS_DIR", unset = "artifacts")
dir.create(artifacts_dir, recursive = TRUE, showWarnings = FALSE)

built <- openair_build_wind_df(payload, include_pollutants = FALSE)
df <- built$df
payload <- built$payload
plot_title <- openair_plot_title(payload)

outfile <- file.path(artifacts_dir, paste0("wind_rose_", format(Sys.time(), "%Y%m%d_%H%M%S"), ".png"))

grDevices::png(outfile, width = 900, height = 900, res = 120)
openair::windRose(df, main = plot_title)
invisible(grDevices::dev.off())

cat(jsonlite::toJSON(list(
  artifact = normalizePath(outfile, winslash = "/", mustWork = FALSE),
  type = "png",
  summary = "Wind rose showing frequency and speed distribution by direction",
  tool = "wind_rose"
), auto_unbox = TRUE))
