"""
	construction.py

	ScalyMUCK construction commands.
	(Dragon sorcery)

	Copyright (c) 2013 Robert MacGregor
	This software is licensed under the GNU General
	Public License version 3. Please refer to gpl.txt 
	for more information.
"""

import string

from blinker import signal

import game.models

class Modification:
	""" Main class object to load and initialize the scommands modification. """
	world = None
	interface = None
	session = None

	work_factor = 10

	def __init__(self, **kwargs):
		self.config = kwargs['config']
		self.interface = kwargs['interface']
		self.session = kwargs['session']
		self.world = kwargs['world']
		signal('post_client_authenticated').connect(self.callback_client_authenticated)
		signal('pre_message_sent').connect(self.callback_message_sent)

	# Callbacks
	def callback_client_authenticated(self, trigger, sender):
		sender.connection.is_editing = False
		sender.connection.edit_target = None
		sender.connection.edit_page = 'main'
		sender.connection.edit_description = ''

	def callback_message_sent(self, trigger, sender, input):
		if (sender.connection.is_editing is True):
			# Perform Action for the main page
			if (sender.connection.edit_page == 'main'):
				if (input == '0'):
					sender.connection.is_editing = False
					sender.send('Stopped editing.')
				elif (input == '1'):
					sender.connection.edit_page = 'name'
					sender.send('Next line you send will be the new name. Leave blank to cancel.')
				elif (input == '2'):
					sender.connection.edit_page = 'description'
					sender.send('Next lines will be appended to your description on their own lines. Send an empty line to exit.')
				elif (input == '3' and type(sender.connection.edit_target) is game.models.Room):
					sender.connection.edit_page = 'exits'
					self.edit_display(sender)
						
				else:
					sender.send('Unknown option.')
			# Perform for when changing a name
			elif (sender.connection.edit_page == 'name'):
				if (input.strip() == ''):
					sender.send('Cancelled name change.')
				else:
					sender.send('Set name to "' + input + '".')
					sender.connection.edit_target.set_name(input)
				sender.connection.edit_page = 'main'
				self.edit_display(sender)
			# Perform for when editing a description
			elif (sender.connection.edit_page == 'description'):
				if (input.strip() == ''):
					sender.connection.edit_target.set_description(sender.connection.edit_description.rstrip())
					sender.send('Description has been changed.')
					sender.connection.edit_page = 'main'
					self.edit_display(sender)
				else:
					sender.connection.edit_description += input + '\n'
			# Perform for when editing the exits
			elif (sender.connection.edit_page == 'exits'):
				if (input == str(len(sender.connection.edit_target.exits))):
					sender.send('Creating Exit. Please type in a name, or leave the line blank to cancel.')
					sender.connection.edit_page = 'exitname'
				elif (input == str(len(sender.connection.edit_target.exits)+1)):
					sender.connection.edit_page = 'main'
					self.edit_display(sender)
				else:
					try:
						selected = int(input)
					except ValueError:
						sender.send('Invalid option.')
						return True
					sender.send('Editing exit.')
					sender.connection.edit_target = sender.connection.edit_target.exits[selected]
			# Perform for when setting a name in the exit creation sequence
			elif (sender.connection.edit_page == 'exitname'):
				if (input.strip() == ''):
					sender.send('Cancelled creation of the exit.')
					sender.connection.edit_page = 'exits'
					self.edit_display(sender)
				else:
					sender.send('Now type in the room ID to attempt to link to.')
					sender.connection.edit_page = 'exitlink'
					sender.connection.exit_name = input
			# Perform for when setting an exit link in the creation sequence
			elif (sender.connection.edit_page == 'exitlink'):
				if (input.strip() == ''):
					sender.send('Cancelled creation of the exit.')
					sender.connection.edit_page = 'exits'
					self.edit_display(sender)
				else:
					try:
						id = int(input)
					except ValueError:
						sender.send('Invalid input.')
						return True

					target = self.world.find_room(id=id)
					if (target is None):
						sender.send('No such room.')
						return True
					elif (target.owner_id != sender.id and sender.is_admin is False):
						sender.send('You do not own that room.')
						return True
					exit = sender.connection.edit_target.add_exit(name=sender.connection.exit_name, target=target, owner=sender)
					sender.send('Exit created successfully.')
					sender.connection.edit_page = 'exits'
					self.edit_display(sender)
					
			return True

	# Edit Menu
	def edit_display(self, sender):
		if (sender.connection.edit_page == 'main'):
			if (type(sender.connection.edit_target) is game.models.Player):
				sender.send('Name: ' + sender.connection.edit_target.display_name)
			else:
				sender.send('Name: ' + sender.connection.edit_target.name)

			sender.send('Available Options: ')
			sender.send('0.) Exit')
			sender.send('1.) Change Name')
			sender.send('2.) Change Description')
			if (type(sender.connection.edit_target) is game.models.Room):
				sender.send('3.) Modify Exits')
		elif (sender.connection.edit_page == 'exits'):
			sender.send('All exits: ')
			if (len(sender.connection.edit_target.exits) != 0):
				for index, exit in enumerate(sender.connection.edit_target.exits):
					sender.send('	' + str(index) + '.) ' + exit.name)
				sender.send('	' + str(index+1) + '.) Create a New Exit')
				sender.send('	' + str(index+2) + '.) Exit')
			else:
				sender.send('	There are no exits to display.')
				sender.send('	0.) Create a New Exit')
				sender.send('	1.) Exit')

	# Commands
	def command_edit(self, **kwargs):
		sender = kwargs['sender']
		input = kwargs['input']

		if (input.lower() == 'here'):
			target = sender.location
		else:
			target = sender.location.find_item(name=input)
		
		if (target is None):
			sender.send('I do not see that.')
			return

		if (target.owner_id != sender.id and sender.is_admin is False):
			sender.send('That is not yours.')
		else:
			sender.send('Editing Object...')
			sender.connection.is_editing = True
			sender.connection.edit_target = target
			sender.connection.edit_page = 'main'
			self.edit_display(sender)

	def command_craft(self, **kwargs):
		sender = kwargs['sender']
		input = kwargs['input']

		if (input.strip() == ''):
			sender.send('Please type in a name.')
		else:
			item = self.world.create_item(name=input, description='<Unset>', owner=sender, location=sender.inventory)
			sender.send('You crafted a "' + input + '".')

	def command_dig(self, **kwargs):
		sender = kwargs['sender']
		input = kwargs['input']

		if (input.strip() == ''):
			sender.send('Please type in a name.')
		else:
			room = self.world.create_room(name=input, description='<Unset>', owner=sender)
			sender.send('Room created. ID: ' + str(room.id))


	def get_commands(self):
		command_dict = {
			'edit':
			{
				'command': self.command_edit,
				'description': 'Edits the target object properties.',
				'usage': 'edit <name>',
				'aliases': [ ],
				'privilege': 0
			},

			'craft':
			{
				'command': self.command_craft,
				'description': 'Crafts an arbitrary item.',
				'usage': 'craft <name>',
				'aliases': [ 'build', 'make' ],
				'privilege': 0
			},

			'dig':
			{
				'command': self.command_dig,
				'description': 'Creates a room and returns the id number.',
				'usage': 'dig <room name>',
				'aliases': [ ],
				'privilege': 0
			}
		}
		return command_dict
