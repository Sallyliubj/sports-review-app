# Database Schema

This schema outlines the structure of the PostgreSQL database used in the Sports Search Web Application.

---

## Tables

### 1. **Users**
Stores information about registered users.

| Column Name | Data Type             | Constraints     |
|-------------|-----------------------|-----------------|
| username    | character varying(20) | `NOT NULL`      |
| coordinate  | character varying(100)| `NOT NULL`      |
| name        | character varying     | `NOT NULL`      |
| age         | integer               |                 |

---

### 2. **Sports**
Stores details about available sports activities.

| Column Name          | Data Type             | Constraints     |
|----------------------|-----------------------|-----------------|
| sport_id             | integer               | `NOT NULL`      |
| coordinate           | character varying(100)| `NOT NULL`      |
| sport_type           | character varying(20) | `NOT NULL`      |
| trail_name           | character varying(100)| `NOT NULL`      |
| difficulty           | character varying(20) | `NOT NULL`      |
| rating               | real                  |                 |
| price                | real                  |                 |
| num_people_completed | integer               |                 |

---

### 3. **Location**
Stores geographic location data.

| Column Name | Data Type             | Constraints     |
|-------------|-----------------------|-----------------|
| coordinate  | character varying(100)| `NOT NULL`      |
| country     | character varying(40) |                 |
| state       | character varying(40) |                 |
| city        | character varying(40) |                 |

---

### 4. **Review**
Stores user reviews for sports activities.

| Column Name      | Data Type            | Constraints     |
|------------------|----------------------|-----------------|
| review_id        | integer              | `NOT NULL`      |
| username         | character varying(20)| `NOT NULL`      |
| sport_id         | integer              | `NOT NULL`      |
| time_written     | date                 | `NOT NULL`      |
| date_completed   | date                 |                 |
| rating           | integer              |                 |
| comments         | character varying    |                 |
| like_count       | integer              |                 |

---

### 5. **Likes**
Stores information about likes on reviews.

| Column Name  | Data Type            | Constraints     |
|--------------|----------------------|-----------------|
| review_id    | integer              | `NOT NULL`      |
| username     | character varying(20)| `NOT NULL`      |
| date_liked   | date                 |                 |

---

### 6. **Needs**
Stores the relationship between sports and required equipment.

| Column Name     | Data Type            | Constraints     |
|-----------------|----------------------|-----------------|
| equipment_name  | character varying    | `NOT NULL`      |
| sport_id        | integer              | `NOT NULL`      |

---

### 7. **Status**
Tracks the status of sports activities for each user.

| Column Name | Data Type            | Constraints     |
|-------------|----------------------|-----------------|
| username    | character varying(20)| `NOT NULL`      |
| sport_id    | integer              | `NOT NULL`      |
| status      | character varying    |                 |

---

### 8. **Equipment**
Stores details about equipment.

| Column Name     | Data Type            | Constraints     |
|-----------------|----------------------|-----------------|
| equipment_name  | character varying    | `NOT NULL`      |
| cost            | real                 |                 |

---

## Notes

- Foreign key relationships are not explicitly defined but should be set up based on the logical relationships:
  - `Users.username` → `Review.username`, `Likes.username`, `Status.username`.
  - `Sports.sport_id` → `Review.sport_id`, `Needs.sport_id`, `Status.sport_id`.
  - `Review.review_id` → `Likes.review_id`.
  - `Location.coordinate` → `Users.coordinate`, `Sports.coordinate`.

