ALTER TABLE places
    ADD COLUMN osm_type text,
    ADD COLUMN osm_id bigint,
    ADD CONSTRAINT places_osm_pair CHECK ((osm_type IS NULL) = (osm_id IS NULL)),
    ADD CONSTRAINT places_osm_type CHECK (osm_type IS NULL OR osm_type IN ('node', 'way', 'relation')),
    ADD CONSTRAINT places_osm_id_positive CHECK (osm_id IS NULL OR osm_id > 0),
    ADD CONSTRAINT places_osm_identity UNIQUE (osm_type, osm_id);
