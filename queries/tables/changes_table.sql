CREATE TABLE changes (
  `source` VARCHAR(255) NOT NULL,
  `event_type` VARCHAR(255) NOT NULL,
  `change_id` VARCHAR(255) NOT NULL UNIQUE,
  `time_created` TIMESTAMP NOT NULL,
  PRIMARY KEY (`change_id`),
  FOREIGN KEY (`change_id`) REFERENCES events_raw(`id`)
);