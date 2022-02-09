CREATE TABLE events_raw (
  `event_type` VARCHAR(255) NOT NULL,
  `id` VARCHAR(255) NOT NULL UNIQUE,
  `metadata` JSON,
  `time_created` TIMESTAMP NOT NULL,
  `signature` VARCHAR(255) NOT NULL,
  `msg_id` VARCHAR(255) NOT NULL,
  `source` VARCHAR(255) NOT NULL,
  PRIMARY KEY (`id`)
);