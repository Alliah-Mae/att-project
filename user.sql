CREATE TABLE `admin_users` (
  `admin_id` int(11) NOT NULL,
  `username` varchar(100) NOT NULL,
  `password` text NOT NULL
)

INSERT INTO `admin_users` (`admin_id`, `username`, `password`) VALUES
(0, 'admin', 'admin123');