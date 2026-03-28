# Technology Stack

## Core Technologies
The application utilizes a lightweight, flexible, yet powerfully extensible ecosystem suited for both rapid prototyping and robust institutional scaling. 

**Backend Engine**: Python 3.x
- Chosen for its immense data science modeling ecosystem (Pandas) which effortlessly parses bulk inputs directly from multi-sheet binary Excel formats without secondary structural adaptations.

**Web Orchestrator**: Flask
- A microframework ideal for tightly coupling Python logic directly into REST-like routing schemas without excessive boilerplating.

**Relational Model (ORM)**: Flask-SQLAlchemy
- Abstracted layer preventing raw SQL reliance. Simplifies mapping Object-Oriented models to complex foreign-key relationships spanning multiple semesters.
- **Current Database Engine**: SQLite (Designed specifically as a file-based prototype for development simplicity; production swaps to PostgreSQL/MySQL are straightforward via URI mapping).

## Data Parsing Layer
**Library**: Pandas & openpyxl
- Allows extraction of unstructured string objects, robust numeric parsing, error trapping across large rows and complex columns, and rapid programmatic regeneration of final computed output spreadsheets exported back to users.

## Frontend Experience (UI/UX)
**Design Philosophy**: Tailwind CSS (Utility-first)
- Embedded structurally via CDN for high contrast, clean, component-level layouts tailored towards data density representations (tables, stats, cards).

**Templating**: Jinja2
- The standard Flask engine used for injecting server-side processed `list`, `dict`, and `ORM Objects` cleanly into iterative HTML displays.

**Client-Side Reactivity**: Vanilla JavaScript & Fetch API (AJAX)
- Modern asynchronous form behaviors to eliminate white-flashing and HTTP roundtrips when evaluating deep structural Excel uploads, keeping the user seamlessly anchored to their workflow context.

## Notifications & Mailing
**Protocol**: SMTP (Flask-Mail)
- Leverages Google App Passwords integration via environment variables (`.env`) to dynamically batch-fire official PDF/HTML memos to localized student email accounts instantaneously upon Admin publication.
