CREATE TABLE incidents (
  `source` VARCHAR(255) NOT NULL,
  `incident_id` VARCHAR(255) NOT NULL UNIQUE,
  `time_created` TIMESTAMP NOT NULL,
  `time_resolved` TIMESTAMP NOT NULL,
  `changes` VARCHAR(255) NOT NULL,
  PRIMARY KEY (`incident_id`)
);