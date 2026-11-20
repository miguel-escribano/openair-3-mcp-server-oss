# MANIFEST: {"name": "dist_plot", "description": "Distribution of pollutant values (histogram, density, freqpoly, or ecdf). Supports openair 3.2 themes and dist_method via plot_options.", "input_type": "series", "output_type": "image", "timeout": 60}
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

outfile <- file.path(artifacts_dir, paste0("dist_plot_", format(Sys.time(), "%Y%m%d_%H%M%S"), ".png"))

grDevices::png(outfile, width = 1000, height = 700, res = 120)
args <- c(
  list(mydata = df, pollutant = pollutant, main = openair_plot_title(payload)),
  openair_dist_plot_extra_args(payload)
)
do.call(openair::distPlot, args)
invisible(grDevices::dev.off())

cat(jsonlite::toJSON(list(
  artifact = normalizePath(outfile, winslash = "/", mustWork = FALSE),
  type = "png",
  summary = paste0("Distribution plot for ", summary_labs[1]),
  tool = "dist_plot"
), auto_unbox = TRUE))