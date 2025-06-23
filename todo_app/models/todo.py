from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError
from datetime import date
import logging

_logger = logging.getLogger(__name__)

class TodoTask(models.Model):
    _name = 'todo.task'
    _description = 'Todo Task'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'priority desc, due_date, id desc'

    name = fields.Char(
        string='Task Name',
        required=True,
        tracking=True,
        size=200,
        help='Enter a clear actionable task name.'
    )
    description = fields.Text(string='Description', size=2000)
    is_done = fields.Boolean(string='Done', default=False, tracking=True)
    active = fields.Boolean(string='Active', default=True, tracking=True)
    
    priority = fields.Selection([
        ('0', 'Low'),
        ('1', 'Normal'),
        ('2', 'Medium'),
        ('3', 'High'),
        ('4', 'Urgent')
    ], string='Priority', default='1', tracking=True)
    
    due_date = fields.Date(string='Due Date', tracking=True)
    created_date = fields.Date(string='Created Date', default=fields.Date.context_today, readonly=True)
    completed_date = fields.Date(string='Completed Date', readonly=True)
    user_id = fields.Many2one('res.users', string='Assigned User', default=lambda self: self.env.user, tracking=True)
    
    kanban_state = fields.Selection([
        ('normal', 'In Progress'),
        ('done', 'Done'),
        ('blocked', 'Blocked')
    ], string='Kanban State', compute='_compute_kanban_state', store=True, default='normal')
    
    is_overdue = fields.Boolean(string='Overdue', compute='_compute_is_overdue', store=True)
    
    status = fields.Selection([
        ('draft', 'Draft'),
        ('todo', 'To Do'),
        ('in_progress', 'In Progress'),
        ('done', 'Done'),
        ('cancelled', 'Cancelled'),
        ('review', 'Under Review')
    ], string='Status', default='todo', tracking=True)
    
    effort_level = fields.Selection([
        ('xs', 'XS (15 min)'),
        ('s', 'S (1 hour)'),
        ('m', 'M (Half day)'),
        ('l', 'L (Full day)'),
        ('xl', 'XL (Multiple days)')
    ], string='Effort Level', default='s', tracking=True)
    
    notes = fields.Text(string='Notes', size=1000)
    progress_percentage = fields.Float(string='Progress %', compute='_compute_progress_percentage', store=True)
    
    time_spent = fields.Integer(string='Time Spent (minutes)', default=0, help='Total time spent on this task in minutes.')
    estimated_time = fields.Integer(string='Estimated Time (minutes)', compute='_compute_estimated_time', store=True, readonly=True, help='Estimated time to complete the task in minutes.')
    task_age_days = fields.Integer(string='Task Age (Days)', compute='_compute_task_age', store=True, readonly=True, help='Number of days since the task was created.')
    
    # Validation constraints
    @api.constrains('name')
    def _check_name_length(self):
        """Validate task name requirements"""
        for task in self:
            if not task.name or not task.name.strip():
                raise ValidationError("Task name cannot be empty.")
            if len(task.name) > 200:
                raise ValidationError("Task name cannot exceed 200 characters.")
            if len(task.name.strip()) < 3:
                raise ValidationError("Task name must be at least 3 characters long.")
    
    @api.constrains('time_spent')
    def _check_time_spent(self):
        """Validate time spent values"""
        for task in self:
            if task.time_spent < 0:
                raise ValidationError("Time spent cannot be negative.")
            if task.time_spent > 100000:
                raise ValidationError("Time spent seems unrealistically high. Please check the value.")
            
    @api.constrains('due_date', 'created_date')
    def _check_due_date(self):
        """Validate due date is not before creation date"""
        for task in self:
            if task.due_date and task.created_date:
                if task.due_date < task.created_date:
                    raise ValidationError("Due date cannot be earlier than the created date.")
    
    @api.constrains('notes', 'description')
    def _check_text_fields(self):
        """Validate text field length limits"""
        for task in self:
            if task.notes and len(task.notes) > 1000:
                raise ValidationError("Notes cannot exceed 1000 characters.")
            if task.description and len(task.description) > 2000:
                raise ValidationError("Description cannot exceed 2000 characters.")
    
    # Computed field methods
    @api.depends('is_done', 'status')
    def _compute_kanban_state(self):
        """Compute kanban state based on task completion and status"""
        for task in self:
            if task.is_done or task.status == 'done':
                task.kanban_state = 'done'
            elif task.status == 'cancelled':
                task.kanban_state = 'blocked'
            else:
                task.kanban_state = 'normal'

    @api.depends('due_date', 'is_done', 'status')
    def _compute_is_overdue(self):
        """Determine if task is overdue based on due date and completion status"""
        today = fields.Date.today()
        for task in self:
            if (task.due_date and not task.is_done and 
                task.status not in ['done', 'cancelled'] and 
                task.due_date < today):
                task.is_overdue = True
            else:
                task.is_overdue = False

    @api.depends('status', 'is_done')
    def _compute_progress_percentage(self):
        """Calculate progress percentage based on status"""
        progress_status = {
            'draft': 0.0,        # 0%
            'todo': 0.1,         # 10%
            'in_progress': 0.5,  # 50%
            'done': 1.0,         # 100%
            'cancelled': 0.0,    # 0%
            'review': 0.75       # 75%
        }
        for task in self:
            if task.is_done or task.status == 'done':
                task.progress_percentage = 1.0  # 100%
            else:
                task.progress_percentage = progress_status.get(task.status, 0.0)
    
    @api.depends('effort_level')
    def _compute_estimated_time(self):
        """Calculate estimated time based on effort level"""
        effort_minutes = {
            'xs': 15,
            's': 60,
            'm': 240,  # 4 hours
            'l': 480,  # 8 hours
            'xl': 1440  # 24 hours
        }
        for task in self:
            task.estimated_time = effort_minutes.get(task.effort_level, 60)
    
    @api.depends('created_date')
    def _compute_task_age(self):
        """Calculate task age in days since creation"""
        today = fields.Date.today()
        for task in self:
            if task.created_date:
                delta = today - task.created_date
                task.task_age_days = delta.days
            else:
                task.task_age_days = 0

    # Action methods
    def action_toggle_done(self):
        """Toggle task completion status with proper date tracking"""
        self.ensure_one()
        if not self.user_has_groups('base.group_user'):
            raise UserError("You do not have permission to toggle task completion.")
        
        try:
            if not self.is_done:
                self.write({
                    'is_done': True,
                    'status': 'done',
                    'completed_date': fields.Date.today()
                })
                self.message_post(body="Task marked as completed!")
                _logger.info(f"Task {self.name} marked as done by {self.env.user.name}.")
            else:
                self.write({
                    'is_done': False,
                    'status': 'todo',
                    'completed_date': False
                })
                self.message_post(body="Task marked as not done!")
                _logger.info(f"Task {self.name} marked as not done by {self.env.user.name}.")
        except Exception as e:
            _logger.error(f"Error toggling task completion: {e}")
            raise UserError(f"Failed to toggle task completion: {e}")
        return True

    def action_start_work(self):
        """Start working on task by setting status to in progress"""
        for task in self:
            if not self.env.user.has_group('base.group_user'):
                raise UserError("Insufficient permissions.")
            
            if task.is_done:
                raise UserError("Cannot start work on completed tasks.")
            
            try:
                task.write({
                    'status': 'in_progress',
                    'is_done': False
                })
                task.message_post(body="Started working on this task!")
                _logger.info(f"Task {task.name} started by {self.env.user.name}.")
            except Exception as e:
                _logger.error(f"Error starting work on task: {e}")
                raise UserError(f"Failed to start work on task: {e}")
        return True

    def action_mark_review(self):
        """Mark task for review"""
        for task in self:
            if not self.env.user.has_group('base.group_user'):
                raise UserError("Insufficient permissions.")
            
            try:
                task.write({
                    'status': 'review',
                    'is_done': False
                })
                task.message_post(body="Task marked for review!")
                _logger.info(f"Task {task.name} marked for review by {self.env.user.name}.")
            except Exception as e:
                _logger.error(f"Error marking task for review: {e}")
                raise UserError(f"Failed to mark task for review: {e}")
        return True

    def action_duplicate_task(self):
        """Create a copy of the current task"""
        self.ensure_one()
        
        if not self.user_has_groups('base.group_user'):
            raise UserError("You don't have permission to duplicate tasks.")
        
        try:
            new_name = f"{self.name[:190]} (Copy)"
            new_task = self.copy({
                'name': new_name,
                'created_date': fields.Date.today(),
                'is_done': False,
                'status': 'todo',
                'completed_date': False,
            })
            new_task.message_post(body=f"Duplicated from task: {self.name}")
            _logger.info(f"Task {self.name} duplicated to {new_task.name} by {self.env.user.name}.")
            
            return {
                'type': 'ir.actions.act_window',
                'name': 'Duplicated Task',
                'res_model': 'todo.task',
                'view_mode': 'form',
                'res_id': new_task.id,
                'target': 'current',
            }
        except Exception as e:
            _logger.error(f"Error duplicating task: {e}")
            raise UserError(f"Failed to duplicate task: {e}")
    
    def action_set_priority_high(self):
        """Set task priority to high"""
        self.ensure_one()
        if not self.user_has_groups('base.group_user'):
            raise UserError("You don't have permission to change task priority.")
        
        try:
            self.write({'priority': '3'})
            self.message_post(body="Priority set to High!")
            _logger.info(f"Priority set to High for task: {self.name} by {self.env.user.name}.")
            return True
        except Exception as e:
            _logger.error(f"Error setting high priority: {e}")
            return False
    
    def action_set_priority_urgent(self):
        """Set task priority to urgent"""
        self.ensure_one()
        if not self.user_has_groups('base.group_user'):
            raise UserError("You don't have permission to set urgent priority.")
        
        try:
            self.write({'priority': '4'})
            self.message_post(body="Priority set to Urgent!")
            _logger.info(f"Priority set to Urgent for task: {self.name} by {self.env.user.name}.")
            return True
        except Exception as e:
            _logger.error(f"Error setting urgent priority: {e}")
            return False
        
    def action_archive(self):
        """Archive tasks by setting active to False"""
        for task in self:
            task.write({'active': False})
            task.message_post(body="Task archived!")
        return True

    def action_unarchive(self):
        """Unarchive tasks by setting active to True"""
        for task in self:
            task.write({'active': True})
            task.message_post(body="Task unarchived!")
        return True

    def action_mark_all_done(self):
        """Mark all selected tasks as done - used by bulk operations"""
        for task in self:
            task.write({
                'is_done': True,
                'status': 'done',
                'completed_date': fields.Date.today()
            })
            task.message_post(body="Bulk action: Marked as completed!")
        return True

    def action_reset_to_todo(self):
        """Reset task to todo status"""
        for task in self:
            task.write({
                'status': 'todo',
                'is_done': False,
                'completed_date': False
            })
            task.message_post(body="Reset to To Do status!")
        return True

    @api.model
    def create(self, vals):
        """Create method with input validation and logging"""
        # Sanitize inputs
        if 'name' in vals:
            vals['name'] = vals['name'].strip()[:200]
        
        if 'description' in vals and vals['description']:
            vals['description'] = vals['description'][:2000]
            
        if 'notes' in vals and vals['notes']:
            vals['notes'] = vals['notes'][:1000]
        
        try:
            task = super(TodoTask, self).create(vals)
            task.message_post(body="New task created!")
            _logger.info(f"New task {task.id} created by user {self.env.user.id}")
            return task
        except Exception as e:
            _logger.error(f"Error creating task: {str(e)}")
            raise UserError(f"Failed to create task: {str(e)}")

    def write(self, vals):
        """Write method with input validation and logging"""
        # Sanitize inputs
        if 'name' in vals:
            vals['name'] = vals['name'].strip()[:200]
            
        if 'description' in vals and vals['description']:
            vals['description'] = vals['description'][:2000]
            
        if 'notes' in vals and vals['notes']:
            vals['notes'] = vals['notes'][:1000]
        
        try:
            result = super(TodoTask, self).write(vals)
            _logger.info(f"Tasks {self.ids} updated by user {self.env.user.id}")
            return result
        except Exception as e:
            _logger.error(f"Error updating tasks {self.ids}: {str(e)}")
            raise UserError(f"Failed to update task: {str(e)}")