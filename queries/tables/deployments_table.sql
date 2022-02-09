CREATE TABLE deployments (
  `deploy_id` VARCHAR(255) NOT NULL UNIQUE,
  `change_id` VARCHAR(255) NOT NULL,
  `project_name` VARCHAR(255),
  `time_created` TIMESTAMP NOT NULL,
  PRIMARY KEY (`deploy_id`),
  FOREIGN KEY (`deploy_id`) REFERENCES events_raw(`id`)
);