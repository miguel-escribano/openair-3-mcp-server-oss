# MANIFEST: {"name": "polar_diff", "description": "Polar plot showing concentration differences between two time periods. series[0] = period A, series[1] = period B (same pollutant, different time ranges).", "input_type": "wind_series", "output_type": "image", "timeout": 120}
if (!requireNamespace("jsonlite", quietly = TRUE)) stop("jsonlite required")
if (!requireNamespace("openair", quietly = TRUE)) stop("openair required")
source(file.path(Sys.getenv("OPENAIR_R_LIB", unset = "r/common"), "series_df.R"))

raw <- paste(readLines(file("stdin"), warn = FALSE), collapse = "")
payload <- jsonlite::fromJSON(raw, simplifyVector = FALSE)

artifacts_dir <- Sys.getenv("OPENAIR_ARTIFACTS_DIR", unset = "artifacts")
dir.create(artifacts_dir, recursive = TRUE, showWarnings = FALSE)

timestamps <- unlist(payload$timestamps)
series_list <- payload$series
if (is.null(payload$ws) || is.null(payload$wd)) stop("ws and wd required")
if (length(series_list) < 2) stop("polar_diff requires two series: period A and period B of the same pollutant")

s1 <- series_list[[1]]
s2 <- series_list[[2]]
p1 <- openair_series_col_id(s1$name, 1)
if (!nzchar(p1)) p1 <- "period_a"
p2 <- openair_series_col_id(s2$name, 2)
if (!nzchar(p2)) p2 <- "period_b"

df <- data.frame(
  date = as.POSIXct(timestamps, format = "%Y-%m-%dT%H:%M:%OSZ", tz = "UTC"),
  ws = as.numeric(unlist(payload$ws)),
  wd = as.numeric(unlist(payload$wd)),
  stringsAsFactors = FALSE
)
pollutant <- p1
before <- data.frame(
  date = df$date,
  ws = df$ws,
  wd = df$wd,
  stringsAsFactors = FALSE
)
before[[pollutant]] <- openair_mcp_values(s1$values, length(timestamps))
after <- data.frame(
  date = df$date,
  ws = df$ws,
  wd = df$wd,
  stringsAsFactors = FALSE
)
after[[pollutant]] <- openair_mcp_values(s2$values, length(timestamps))

plot_title <- openair_plot_title(payload)
summary_labs <- openair_summary_labels(payload)

outfile <- file.path(artifacts_dir, paste0("polar_diff_", format(Sys.time(), "%Y%m%d_%H%M%S"), ".png"))

grDevices::png(outfile, width = 1200, height = 600, res = 120)
openair::polarDiff(before, after, pollutant = pollutant, main = plot_title)
invisible(grDevices::dev.off())

cat(jsonlite::toJSON(list(
  artifact = normalizePath(outfile, winslash = "/", mustWork = FALSE),
  type = "png",
  summary = paste0("Polar difference: ", summary_labs[1], " vs ", summary_labs[2]),
  tool = "polar_diff"
), auto_unbox = TRUE))
