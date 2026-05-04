#!/usr/bin/env bash
# =============================================================================
# influx_setup.sh — Create InfluxDB bucket + measurement schemas
#
# Usage:
#   chmod +x influx_setup.sh
#   ./influx_setup.sh
#
# Environment variables (override defaults as needed):
#   INFLUX_URL    — default: http://localhost:8086
#   INFLUX_TOKEN  — default: my-super-secret-token
#   INFLUX_ORG    — default: myorg
#   INFLUX_BUCKET — default: iot_factory
# =============================================================================

set -euo pipefail

INFLUX_URL="${INFLUX_URL:-http://localhost:8086}"
INFLUX_TOKEN="${INFLUX_TOKEN:-my-super-secret-token}"
INFLUX_ORG="${INFLUX_ORG:-myorg}"
INFLUX_BUCKET="${INFLUX_BUCKET:-iot_factory}"
RETENTION="30d"   # keep data for 30 days

echo "══════════════════════════════════════════════════"
echo " InfluxDB Schema Setup"
echo " URL    : $INFLUX_URL"
echo " Org    : $INFLUX_ORG"
echo " Bucket : $INFLUX_BUCKET"
echo "══════════════════════════════════════════════════"

# ── 1. Wait for InfluxDB to be ready ────────────────────────────────────────
echo ""
echo "⏳  Waiting for InfluxDB to be ready..."
until curl -sf "$INFLUX_URL/health" | grep -q '"status":"pass"'; do
  sleep 2
  echo "   ...still waiting"
done
echo "✅  InfluxDB is up"

# ── 2. Create bucket (ignore error if it already exists) ────────────────────
echo ""
echo "📦  Creating bucket: $INFLUX_BUCKET (retention: $RETENTION)"

influx bucket create \
  --name "$INFLUX_BUCKET" \
  --org "$INFLUX_ORG" \
  --retention "$RETENTION" \
  --host "$INFLUX_URL" \
  --token "$INFLUX_TOKEN" 2>/dev/null \
  && echo "✅  Bucket created" \
  || echo "ℹ️   Bucket already exists — skipping"

# ── 3. Seed valve_telemetry measurement ─────────────────────────────────────
# InfluxDB v2 schemas are created implicitly on first write.
# We write one bootstrap point so the measurement and field types are locked.
echo ""
echo "📐  Seeding measurement: valve_telemetry"

influx write \
  --bucket "$INFLUX_BUCKET" \
  --org "$INFLUX_ORG" \
  --host "$INFLUX_URL" \
  --token "$INFLUX_TOKEN" \
  --precision s \
  "valve_telemetry,site_id=INIT,metric=barrage_valve_percent,mqtt_topic=factory/line1/telemetry/barrage_valve_percent value=0.0 $(date +%s)"

echo "✅  valve_telemetry measurement ready"

# ── 4. Seed gaz_telemetry measurement ───────────────────────────────────────
echo ""
echo "📐  Seeding measurement: gaz_telemetry"

influx write \
  --bucket "$INFLUX_BUCKET" \
  --org "$INFLUX_ORG" \
  --host "$INFLUX_URL" \
  --token "$INFLUX_TOKEN" \
  --precision s \
  "gaz_telemetry,site_id=INIT,metric=voc_gas_raw,mqtt_topic=factory/line1/telemetry/voc_gas_raw value=0.0 $(date +%s)"

echo "✅  gaz_telemetry measurement ready"

# ── 5. Enable explicit schema (optional — prevents unknown fields) ───────────
# Uncomment the blocks below if you want strict schema enforcement.
# Requires InfluxDB v2.3+ with --features=schema enforcement enabled.

# echo ""
# echo "🔒  Applying explicit column schemas..."
#
# influx bucket-schema create \
#   --bucket "$INFLUX_BUCKET" \
#   --org "$INFLUX_ORG" \
#   --host "$INFLUX_URL" \
#   --token "$INFLUX_TOKEN" \
#   --name valve_telemetry \
#   --columns-file /dev/stdin <<'EOF'
# [{"name":"time","type":"timestamp"},
#  {"name":"site_id","type":"tag"},
#  {"name":"metric","type":"tag"},
#  {"name":"mqtt_topic","type":"tag"},
#  {"name":"value","type":"field","dataType":"float"}]
# EOF
#
# influx bucket-schema create \
#   --bucket "$INFLUX_BUCKET" \
#   --org "$INFLUX_ORG" \
#   --host "$INFLUX_URL" \
#   --token "$INFLUX_TOKEN" \
#   --name gaz_telemetry \
#   --columns-file /dev/stdin <<'EOF'
# [{"name":"time","type":"timestamp"},
#  {"name":"site_id","type":"tag"},
#  {"name":"metric","type":"tag"},
#  {"name":"mqtt_topic","type":"tag"},
#  {"name":"value","type":"field","dataType":"float"}]
# EOF

# ── 6. Verify ───────────────────────────────────────────────────────────────
echo ""
echo "🔍  Verifying measurements..."

influx query \
  --org "$INFLUX_ORG" \
  --host "$INFLUX_URL" \
  --token "$INFLUX_TOKEN" \
  'import "influxdata/influxdb/schema"
   schema.measurements(bucket: "'"$INFLUX_BUCKET"'")'

echo ""
echo "══════════════════════════════════════════════════"
echo "✅  InfluxDB setup complete!"
echo ""
echo "   Measurements created:"
echo "   • valve_telemetry  (tags: site_id, metric, mqtt_topic | field: value float)"
echo "   • gaz_telemetry    (tags: site_id, metric, mqtt_topic | field: value float)"
echo "══════════════════════════════════════════════════"