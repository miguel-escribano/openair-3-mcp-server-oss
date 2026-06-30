# Shared SeriesV1 ↔ data.frame helpers for openair-3-mcp R scripts.

#' Map JSON series values to a fixed-length numeric vector (null → NA).
openair_mcp_values <- function(values, n) {
  if (missing(n) || is.null(n) || !is.finite(n) || n < 0) {
    stop("openair_mcp_values: n (expected row count) is required")
  }
  n <- as.integer(n)
  out <- rep(NA_real_, n)
  if (is.null(values) || length(values) == 0) {
    return(out)
  }
  if (is.list(values) && !is.data.frame(values)) {
    len <- min(n, length(values))
    for (i in seq_len(len)) {
      v <- values[[i]]
      if (!is.null(v)) {
        out[i] <- as.numeric(v)
      }
    }
    return(out)
  }
  vals <- as.numeric(values)
  len <- min(n, length(vals))
  if (len > 0) {
    out[seq_len(len)] <- vals[seq_len(len)]
  }
  out
}

#' Column names that are never pollutant series when importing openair data.frames.
openair_skip_series_cols <- function() {
  c(
    "date", "ws", "wd", "wind_speed", "wind_direction",
    "lat", "lon", "latitude", "longitude",
    "code", "site", "site_type", "network", "type",
    "rain", "precip", "solar", "temp", "air_temp", "rh", "humidity"
  )
}

#' Repair UTF-8 mojibake (UTF-8 bytes misread as Latin-1), e.g. DiÃ³xido → Dióxido.
openair_fix_mojibake <- function(x) {
  s <- as.character(x)[1]
  if (is.na(s) || !nzchar(s)) return(s)
  if (!grepl("Ã|Â|â€", s)) return(s)
  chars <- strsplit(s, "", fixed = FALSE)[[1]]
  bytes <- vapply(chars, function(ch) {
    cp <- utf8ToInt(ch)
    if (length(cp) != 1L || cp > 255L) return(NA_integer_)
    cp
  }, integer(1))
  if (any(is.na(bytes))) return(s)
  out <- tryCatch(
    iconv(rawToChar(as.raw(bytes)), from = "UTF-8", to = "UTF-8"),
    error = function(e) NA_character_
  )
  if (is.na(out) || !nzchar(out)) s else out
}

#' Normalize series/column labels before id mapping and display.
openair_normalize_label <- function(x) {
  s <- trimws(as.character(x)[1])
  if (is.na(s) || !nzchar(s)) return(s)
  openair_fix_mojibake(s)
}

#' Short openair-safe column id (lowercase per openair book §2.2).
openair_series_col_id <- function(name, index = 1L) {
  nm <- tolower(openair_normalize_label(name))
  if (grepl("pm2\\.?5|2\\.5", nm)) return("pm25")
  if (grepl("pm10|10.?µm|10.?um|10.?\\u00b5m|part.{0,2}culas|particulas", nm)) return("pm10")
  if (grepl("no2|nitr", nm)) return("no2")
  if (grepl("nox", nm)) return("nox")
  if (grepl("o3|ozon", nm)) return("o3")
  if (grepl("so2|azufre", nm)) return("so2")
  if (grepl("co2", nm)) return("co2")
  if (grepl("^co$|carbon.mon", nm)) return("co")
  if (nm %in% c("ws", "wd", "pm25", "pm10", "no2", "nox", "o3", "so2", "co2", "co")) {
    return(nm)
  }
  col <- gsub("[^A-Za-z0-9_.]", "_", as.character(name))
  col <- tolower(col)
  col <- gsub("_+", "_", col)
  col <- sub("^_|_$", "", col)
  if (!nzchar(col)) col <- paste0("poll", index)
  if (nchar(col) > 32) col <- substr(col, 1, 32)
  col
}

#' Human-readable label for MCP text (original name + unit).
openair_series_display_label <- function(s) {
  nm <- if (!is.null(s$name)) openair_normalize_label(s$name) else "value"
  u <- if (!is.null(s$unit)) openair_normalize_label(s$unit) else ""
  if (nzchar(u)) paste0(nm, " (", u, ")") else nm
}

#' Short pollutant ids for MCP text and plot titles (openair auto.text handles legends).
openair_summary_labels <- function(payload) {
  series <- payload$series
  if (is.null(series) || length(series) == 0) return(character(0))
  vapply(seq_along(series), function(i) {
    openair_series_col_id(series[[i]]$name, i)
  }, character(1))
}

#' Ensure payload carries meta.timezone (from meta or prepare's top-level timezone).
openair_payload_meta <- function(payload) {
  if (is.null(payload$meta) || !is.list(payload$meta)) {
    payload$meta <- list()
  }
  tz <- payload$meta$timezone
  if (is.null(tz) || !nzchar(as.character(tz)[1])) {
    if (!is.null(payload$timezone) && nzchar(as.character(payload$timezone)[1])) {
      payload$meta$timezone <- as.character(payload$timezone)
    }
  }
  payload$meta <- openair_sanitize_meta(payload$meta)
  payload
}

#' Drop null/NA/empty lat-lon and other invalid meta fields before JSON export.
openair_sanitize_meta <- function(meta) {
  if (is.null(meta) || !is.list(meta)) return(NULL)
  bad <- function(v) {
    is.null(v) || length(v) == 0 || (length(v) == 1 && (is.na(v) || is.nan(v)))
  }
  if (!is.null(meta$lat) && bad(meta$lat)) meta$lat <- NULL
  if (!is.null(meta$lon) && bad(meta$lon)) meta$lon <- NULL
  keep <- vapply(meta, function(v) !is.null(v) && !(is.list(v) && length(v) == 0), logical(1))
  if (!any(keep)) return(NULL)
  meta[keep]
}

#' Pick avg.time for trend/resample tools from span when caller omits it.
openair_infer_avg_time <- function(dates, default = "month") {
  if (length(dates) < 2) return(default)
  d <- dates[!is.na(dates)]
  if (length(d) < 2) return(default)
  span_days <- as.numeric(difftime(max(d), min(d), units = "days"))
  if (span_days < 60) return("day")
  if (span_days < 730) return("month")
  default
}

#' Copy meta list from payload for series-out transform tools.
openair_meta_out <- function(payload) {
  payload <- openair_payload_meta(payload)
  if (is.null(payload$meta) || !is.list(payload$meta)) return(NULL)
  payload$meta
}

#' Re-tag a UTC POSIXct vector to a local IANA zone for DISPLAY only.
openair_localize_dates <- function(dates, payload) {
  tz <- NULL
  if (!is.null(payload$meta) && !is.null(payload$meta$timezone)) {
    tzc <- as.character(payload$meta$timezone)
    if (length(tzc) == 1 && !is.na(tzc) && nzchar(tzc)) tz <- tzc
  }
  if (is.null(tz) && !is.null(payload$timezone)) {
    tzc <- as.character(payload$timezone)
    if (length(tzc) == 1 && !is.na(tzc) && nzchar(tzc)) tz <- tzc
  }
  if (is.null(tz)) {
    return(dates)
  }
  tryCatch({
    attr(dates, "tzone") <- tz
    dates
  }, error = function(e) dates)
}

#' Numeric pollutant columns from an openair import data.frame.
openair_pollutant_cols <- function(data) {
  skip <- tolower(openair_skip_series_cols())
  names(data)[sapply(data, is.numeric) & !tolower(names(data)) %in% skip]
}

#' Build SeriesV1 meta from openair import df + caller meta list.
openair_import_meta <- function(data, meta = list()) {
  if (is.null(meta) || !is.list(meta)) meta <- list()
  if ("latitude" %in% names(data) && is.null(meta$lat)) {
    v <- data$latitude[!is.na(data$latitude)]
    if (length(v) > 0) meta$lat <- as.numeric(v[1])
  }
  if ("longitude" %in% names(data) && is.null(meta$lon)) {
    v <- data$longitude[!is.na(data$longitude)]
    if (length(v) > 0) meta$lon <- as.numeric(v[1])
  }
  if ("lat" %in% names(data) && is.null(meta$lat)) {
    v <- data$lat[!is.na(data$lat)]
    if (length(v) > 0) meta$lat <- as.numeric(v[1])
  }
  if ("lon" %in% names(data) && is.null(meta$lon)) {
    v <- data$lon[!is.na(data$lon)]
    if (length(v) > 0) meta$lon <- as.numeric(v[1])
  }
  if ("site" %in% names(data) && is.null(meta$site)) {
    v <- as.character(data$site[!is.na(data$site)])
    if (length(v) > 0) meta$site <- v[1]
  }
  meta
}

#' openair data.frame → SeriesV1 JSON list (stdout-ready).
openair_df_to_seriesv1 <- function(data, meta = list()) {
  if (is.null(data) || nrow(data) == 0) stop("empty data.frame")
  if (!"date" %in% names(data)) stop("data.frame must contain date column")
  meta <- openair_import_meta(data, meta)
  meta <- openair_sanitize_meta(meta)
  pollutant_cols <- openair_pollutant_cols(data)
  if (length(pollutant_cols) == 0) stop("no pollutant columns found in import")
  timestamps <- format(as.POSIXct(data$date, tz = "UTC"), "%Y-%m-%dT%H:%M:%SZ")
  series <- lapply(pollutant_cols, function(col) {
    list(name = col, unit = "", values = as.list(data[[col]]))
  })
  list(timestamps = timestamps, series = series, meta = meta)
}

#' Build date + pollutant data.frame with short column ids.
openair_build_series_df <- function(payload, localize_dates = TRUE) {
  payload <- openair_payload_meta(payload)
  timestamps <- unlist(payload$timestamps)
  series_list <- payload$series
  if (is.null(timestamps) || length(timestamps) == 0) stop("timestamps required")
  if (is.null(series_list) || length(series_list) == 0) stop("series required")

  df <- data.frame(
    date = as.POSIXct(timestamps, format = "%Y-%m-%dT%H:%M:%OSZ", tz = "UTC"),
    stringsAsFactors = FALSE
  )
  if (localize_dates) {
    df$date <- openair_localize_dates(df$date, payload)
  }
  if (!is.null(payload$meta) && !is.null(payload$meta$site)) {
    st <- as.character(payload$meta$site)
    if (length(st) == 1 && !is.na(st) && nzchar(st) && st != "multi_device") {
      df$site <- st
    }
  }

  pollutants <- character(length(series_list))
  labels <- character(length(series_list))
  used <- character(0)
  for (i in seq_along(series_list)) {
    s <- series_list[[i]]
    col <- openair_series_col_id(s$name, i)
    if (col %in% used) col <- paste0(col, "_", i)
    used <- c(used, col)
    pollutants[i] <- col
    labels[i] <- openair_series_display_label(s)
    df[[col]] <- openair_mcp_values(s$values, length(timestamps))
  }
  list(df = df, pollutants = pollutants, labels = labels, payload = payload)
}

#' WindSeriesV1 → data.frame (ws, wd, optional pollutants).
openair_build_wind_df <- function(payload, localize_dates = TRUE, include_pollutants = TRUE) {
  payload <- openair_payload_meta(payload)
  timestamps <- unlist(payload$timestamps)
  if (is.null(timestamps) || length(timestamps) == 0) stop("timestamps required")
  if (is.null(payload$ws) || is.null(payload$wd)) stop("ws and wd required")

  df <- data.frame(
    date = as.POSIXct(timestamps, format = "%Y-%m-%dT%H:%M:%OSZ", tz = "UTC"),
    ws = as.numeric(unlist(payload$ws)),
    wd = as.numeric(unlist(payload$wd)),
    stringsAsFactors = FALSE
  )
  if (localize_dates) {
    df$date <- openair_localize_dates(df$date, payload)
  }

  pollutants <- character(0)
  if (isTRUE(include_pollutants)) {
    series_list <- payload$series
    if (!is.null(series_list) && length(series_list) > 0) {
      used <- character(0)
      for (i in seq_along(series_list)) {
        s <- series_list[[i]]
        col <- openair_series_col_id(s$name, i)
        if (col %in% used) col <- paste0(col, "_", i)
        used <- c(used, col)
        pollutants[i] <- col
        df[[col]] <- openair_mcp_values(s$values, length(timestamps))
      }
    }
  }

  list(df = df, pollutants = pollutants, payload = payload)
}

#' Plot title: site · pollutant · period (timezone).
openair_plot_title <- function(payload) {
  payload <- openair_payload_meta(payload)
  tz <- "UTC"
  if (!is.null(payload$meta) && !is.null(payload$meta$timezone)) {
    tzc <- as.character(payload$meta$timezone)
    if (length(tzc) == 1 && !is.na(tzc) && nzchar(tzc)) tz <- tzc
  }

  labels <- character(0)
  series <- payload$series
  if (!is.null(series)) {
    for (i in seq_along(series)) {
      labels <- c(labels, openair_series_col_id(series[[i]]$name, i))
    }
  }
  labels <- unique(labels)
  if (length(labels) > 3) {
    params <- paste0(paste(labels[1:3], collapse = ", "), " +", length(labels) - 3, " more")
  } else {
    params <- paste(labels, collapse = ", ")
  }

  period <- NULL
  ts <- tryCatch(unlist(payload$timestamps), error = function(e) NULL)
  if (!is.null(ts) && length(ts) > 0) {
    d <- as.POSIXct(ts, format = "%Y-%m-%dT%H:%M:%OSZ", tz = "UTC")
    d <- d[!is.na(d)]
    if (length(d) > 0) {
      lo <- min(d)
      hi <- max(d)
      attr(lo, "tzone") <- tz
      attr(hi, "tzone") <- tz
      if (identical(format(lo, "%Y-%m-%d"), format(hi, "%Y-%m-%d"))) {
        period <- format(lo, "%d %b %Y")
      } else if (identical(format(lo, "%Y-%m"), format(hi, "%Y-%m"))) {
        period <- paste0(format(lo, "%d"), "–", format(hi, "%d %b %Y"))
      } else {
        period <- paste0(format(lo, "%d %b %Y"), " – ", format(hi, "%d %b %Y"))
      }
    }
  }

  site <- NULL
  if (!is.null(payload$meta) && !is.null(payload$meta$site)) {
    s <- as.character(payload$meta$site)
    if (length(s) == 1 && !is.na(s) && nzchar(s) && s != "multi_device") {
      site <- s
    }
  }

  bits <- character(0)
  if (!is.null(site)) bits <- c(bits, site)
  if (nzchar(params)) bits <- c(bits, params)
  if (!is.null(period)) bits <- c(bits, paste0(period, " (", tz, ")"))
  paste(bits, collapse = " · ")
}

#' Resolve an openair function safely (namespace → package → search path).
openair_resolve_fn <- function(fn_name) {
  fn <- tryCatch(
    get(fn_name, envir = asNamespace("openair"), inherits = FALSE),
    error = function(e) NULL
  )
  if (!is.null(fn) && is.function(fn)) return(fn)
  fn <- tryCatch(
    get(fn_name, envir = as.environment("package:openair"), inherits = FALSE),
    error = function(e) NULL
  )
  if (!is.null(fn) && is.function(fn)) return(fn)
  fn <- tryCatch(get(fn_name, inherits = TRUE), error = function(e) NULL)
  if (!is.null(fn) && is.function(fn)) return(fn)
  stop(paste0("Cannot find openair function '", fn_name, "'."))
}

#' Stop with a clear message when required columns are missing.
openair_req_cols <- function(df, cols) {
  cols <- cols[nchar(cols) > 0]
  missing <- setdiff(cols, names(df))
  if (length(missing) > 0) {
    stop(paste0(
      "Column(s) not in data: ", paste(missing, collapse = ", "),
      ". Available: ", paste(names(df), collapse = ", ")
    ))
  }
}

#' Filter pollutant names to those present in df; stop if none remain.
openair_clean_poll <- function(df, polls, allow_empty = FALSE) {
  if (is.null(polls)) polls <- character(0)
  polls <- polls[nchar(polls) > 0]
  polls <- intersect(polls, names(df))
  if (length(polls) == 0) {
    if (allow_empty) return(character(0))
    avail <- openair_pollutant_cols(df)
    stop(paste0(
      "None of the selected pollutant columns exist in the data. ",
      "Available: ", paste(avail, collapse = ", ")
    ))
  }
  polls
}
