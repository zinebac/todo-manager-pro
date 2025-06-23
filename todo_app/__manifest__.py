{
    'name': 'Todo Manager',
    'version': '17.0.2.0.0',
    'category': 'Productivity',
    'summary': 'Professional task management with advanced features',
    'description': """
    Professional Todo Management Application
    ========================================
    
    A comprehensive task management solution designed for professional teams and individual productivity.
    
    Core Features:
    - Clean, modern interface with professional design
    - Advanced task prioritization and effort tracking
    - Multiple view modes (Kanban, Tree, Form)
    - Due date management with overdue detection
    - User assignment and collaboration features
    - Progress tracking with visual indicators
    - Bulk operations for efficiency
    - Archive and restore functionality
    - Advanced search and filtering capabilities
    - Professional typography and responsive design
    - Accessibility improvements
    
    Technical Features:
    - Comprehensive security model with record rules
    - Mail integration with activity tracking
    - Professional CSS styling with modern components
    - Extensive validation and error handling
    - Logging and audit trail capabilities
    - Performance optimized queries
    
    Use Cases:
    - Project management teams
    - Software development workflows
    - Business process management
    - Personal productivity tracking
    - Team collaboration and task assignment
    """,
    'author': 'ZAC',
    'depends': [
        'base',
        'mail',
        'web'
    ],
    'data': [
        'security/ir.model.access.csv',
        'security/todo_security.xml',
        'views/todo_views.xml',
        'views/bulk_actions.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'todo_app/static/src/css/todo_style.css',
        ],
    },
    'images': [
        'static/description/banner.png',
        'static/description/icon.png',
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
    'license': 'MIT',
    'external_dependencies': {
        'python': [],
        'bin': []
    },
    'post_init_hook': None,
    'uninstall_hook': None,
}