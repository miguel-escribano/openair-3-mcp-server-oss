# MANIFEST: {"name": "import_aurn_csv", "description": "Import UK AURN hourly CSV export from server disk via openair::importAURNCsv. Returns SeriesV1-compatible JSON.", "input_type": "file_import", "output_type": "series", "timeout": 120}
if (!requireNamespace("jsonlite", quietly = TRUE)) stop("jsonlite required")
if (!requireNamespace("openair", quietly = TRUE)) stop("openair required")
source(file.path(Sys.getenv("OPENAIR_R_LIB", unset = "r/common"), "series_df.R"))

raw <- paste(readLines(file("stdin"), warn = FALSE), collapse = "")
payload <- jsonlite::fromJSON(raw, simplifyVector = FALSE)

path <- payload$path
if (is.null(path) || !nzchar(as.character(path)[1])) stop("path required (file on MCP server host)")
if (!file.exists(path)) stop(paste0("file not found: ", path))

simplify <- if (!is.null(payload$simplify_names)) isTRUE(payload$simplify_names) else TRUE

data <- openair::importAURNCsv(file = path, simplify.names = simplify)
if (is.null(data) || nrow(data) == 0) stop(paste0("No data imported from ", path))

meta <- list(source = "aurn_csv")
if (!is.null(payload$site) && nzchar(as.character(payload$site)[1])) {
  meta$site <- as.character(payload$site)
} else if ("site" %in% names(data)) {
  meta$site <- as.character(data$site[!is.na(data$site)][1])
}
if (!is.null(payload$timezone) && nzchar(as.character(payload$timezone)[1])) {
  meta$timezone <- as.character(payload$timezone)
}

out <- openair_df_to_seriesv1(data, meta = meta)
cat(jsonlite::toJSON(out, auto_unbox = TRUE, na = "null"))
