"""
Admin cog for ATENA-AI Discord bot.
Handles bot administration, settings management, and permissions.
"""

import discord
from discord.ext import commands
import asyncio
import logging
from typing import Dict, List, Optional, Any
import json
from datetime import datetime

logger = logging.getLogger(__name__)

class Admin(commands.Cog):
    """Admin cog for ATENA-AI."""
    
    def __init__(self, bot):
        """Initialize the Admin cog."""
        self.bot = bot
        self.config = self._load_config()
        self.admin_roles: Dict[int, List[int]] = {}
        self.command_cooldowns: Dict[str, Dict[int, datetime]] = {}
    
    def _load_config(self) -> Dict[str, Any]:
        """Load admin configuration."""
        try:
            with open('config.json', 'r') as f:
                config = json.load(f)
                return config.get('admin', {
                    'command_cooldown': 3,
                    'max_admin_roles': 3,
                    'allowed_channels': [],
                    'restricted_commands': []
                })
        except FileNotFoundError:
            logger.warning("config.json not found, using default configuration")
            return {
                'command_cooldown': 3,
                'max_admin_roles': 3,
                'allowed_channels': [],
                'restricted_commands': []
            }
    
    def cog_check(self, ctx):
        """Check if user has admin permissions."""
        return self._is_admin(ctx.author)
    
    def _is_admin(self, member: discord.Member) -> bool:
        """Check if a member has admin permissions."""
        # Check if user is bot owner
        if member.id == self.bot.owner_id:
            return True
        
        # Check admin roles
        guild_roles = self.admin_roles.get(member.guild.id, [])
        return any(role.id in guild_roles for role in member.roles)
    
    @commands.group(name='admin')
    async def admin_group(self, ctx):
        """Admin command group."""
        if ctx.invoked_subcommand is None:
            await ctx.send(
                "Available admin commands:\n"
                "`!admin setup` - Set up admin roles\n"
                "`!admin settings` - View current settings\n"
                "`!admin channels` - Manage allowed channels\n"
                "`!admin cooldown` - Set command cooldown\n"
                "`!admin reload` - Reload bot cogs"
            )
    
    @admin_group.command(name='setup')
    async def setup_admin(self, ctx):
        """Set up admin roles for the guild."""
        try:
            # Check if already set up
            if ctx.guild.id in self.admin_roles:
                await ctx.send("Admin roles are already set up. Use `!admin settings` to view them.")
                return
            
            # Create admin role if it doesn't exist
            admin_role = discord.utils.get(ctx.guild.roles, name='ATENA Admin')
            if not admin_role:
                admin_role = await ctx.guild.create_role(
                    name='ATENA Admin',
                    permissions=discord.Permissions(
                        manage_messages=True,
                        manage_channels=True,
                        manage_roles=True
                    )
                )
            
            # Store admin role
            self.admin_roles[ctx.guild.id] = [admin_role.id]
            
            # Assign role to command user
            await ctx.author.add_roles(admin_role)
            
            await ctx.send(f"✅ Admin role set up: {admin_role.mention}")
            
        except Exception as e:
            logger.error(f"Error setting up admin: {e}")
            await ctx.send("Failed to set up admin role.")
    
    @admin_group.command(name='settings')
    async def show_settings(self, ctx):
        """Show current admin settings."""
        try:
            embed = discord.Embed(
                title="Admin Settings",
                color=discord.Color.blue()
            )
            
            # Add admin roles
            roles = self.admin_roles.get(ctx.guild.id, [])
            role_mentions = [
                ctx.guild.get_role(role_id).mention
                for role_id in roles
                if ctx.guild.get_role(role_id)
            ]
            
            embed.add_field(
                name="Admin Roles",
                value="\n".join(role_mentions) if role_mentions else "None",
                inline=False
            )
            
            # Add allowed channels
            channels = self.config['allowed_channels']
            channel_mentions = [
                ctx.guild.get_channel(channel_id).mention
                for channel_id in channels
                if ctx.guild.get_channel(channel_id)
            ]
            
            embed.add_field(
                name="Allowed Channels",
                value="\n".join(channel_mentions) if channel_mentions else "All",
                inline=False
            )
            
            # Add command cooldown
            embed.add_field(
                name="Command Cooldown",
                value=f"{self.config['command_cooldown']} seconds",
                inline=True
            )
            
            # Add restricted commands
            restricted = self.config['restricted_commands']
            embed.add_field(
                name="Restricted Commands",
                value="\n".join(f"• {cmd}" for cmd in restricted) if restricted else "None",
                inline=False
            )
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error showing settings: {e}")
            await ctx.send("Failed to retrieve admin settings.")
    
    @admin_group.command(name='channels')
    async def manage_channels(self, ctx, action: str, channel: discord.TextChannel):
        """Manage allowed channels."""
        try:
            if action.lower() == 'add':
                if channel.id not in self.config['allowed_channels']:
                    self.config['allowed_channels'].append(channel.id)
                    await ctx.send(f"✅ Added {channel.mention} to allowed channels.")
                else:
                    await ctx.send(f"{channel.mention} is already in allowed channels.")
            
            elif action.lower() == 'remove':
                if channel.id in self.config['allowed_channels']:
                    self.config['allowed_channels'].remove(channel.id)
                    await ctx.send(f"✅ Removed {channel.mention} from allowed channels.")
                else:
                    await ctx.send(f"{channel.mention} is not in allowed channels.")
            
            else:
                await ctx.send("Invalid action. Use 'add' or 'remove'.")
            
            # Save updated config
            self._save_config()
            
        except Exception as e:
            logger.error(f"Error managing channels: {e}")
            await ctx.send("Failed to manage channels.")
    
    @admin_group.command(name='cooldown')
    async def set_cooldown(self, ctx, seconds: int):
        """Set command cooldown in seconds."""
        try:
            if seconds < 0:
                await ctx.send("Cooldown cannot be negative.")
                return
            
            self.config['command_cooldown'] = seconds
            self._save_config()
            
            await ctx.send(f"✅ Set command cooldown to {seconds} seconds.")
            
        except Exception as e:
            logger.error(f"Error setting cooldown: {e}")
            await ctx.send("Failed to set command cooldown.")
    
    @admin_group.command(name='reload')
    async def reload_cogs(self, ctx):
        """Reload all bot cogs."""
        try:
            await ctx.send("🔄 Reloading cogs...")
            
            # Get list of cogs
            cogs = [
                'src.discord_bot.cogs.business_intelligence',
                'src.discord_bot.cogs.conversation',
                'src.discord_bot.cogs.notifications',
                'src.discord_bot.cogs.admin'
            ]
            
            # Reload each cog
            for cog in cogs:
                try:
                    self.bot.reload_extension(cog)
                    logger.info(f"Reloaded cog: {cog}")
                except Exception as e:
                    logger.error(f"Failed to reload cog {cog}: {e}")
            
            await ctx.send("✅ Cogs reloaded successfully.")
            
        except Exception as e:
            logger.error(f"Error reloading cogs: {e}")
            await ctx.send("Failed to reload cogs.")
    
    def _save_config(self):
        """Save updated configuration to config.json."""
        try:
            with open('config.json', 'r') as f:
                config = json.load(f)
            
            # Update admin section
            config['admin'] = self.config
            
            # Write back to file
            with open('config.json', 'w') as f:
                json.dump(config, f, indent=4)
            
        except Exception as e:
            logger.error(f"Error saving config: {e}")

def setup(bot):
    """Set up the Admin cog."""
    bot.add_cog(Admin(bot)) 