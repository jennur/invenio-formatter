# -*- coding: utf-8 -*-
## $Id$
## Bibformt Migration Kit. Migrate previous php Bibformat config files to
## new python Bibformat files.

## This file is part of CDS Invenio.
## Copyright (C) 2002, 2003, 2004, 2005 CERN.
##
## The CDSware is free software; you can redistribute it and/or
## modify it under the terms of the GNU General Public License as
## published by the Free Software Foundation; either version 2 of the
## License, or (at your option) any later version.
##
## The CDSware is distributed in the hope that it will be useful, but
## WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
## General Public License for more details.
##
## You should have received a copy of the GNU General Public License
## along with CDSware; if not, write to the Free Software Foundation, Inc.,
## 59 Temple Place, Suite 330, Boston, MA 02111-1307, USA.

import re
import sys
import os
import StringIO
import time

from invenio.errorlib import *
from invenio.config import *
from invenio.bibformat_dblayer import *
from invenio.bibformat_migration_kit_dblayer import *

from invenio.bibformat_config import format_template_extension, format_output_extension, templates_path, elements_path, outputs_path

#from invenio.bibformat_migration_kit.bibformat_yacc import translate_format #TEMP DISABLED FIXME

#Regular expression for finding attribute in format_exist function in old behaviours
#Used when parsing output formats
pattern_parse_format_exist = re.compile('''
     format_exist\(          
     \s*
     ((?P<sep1>[\'"])
     (?P<prefix>.*?)
     (?P=sep1))?
     
     (?P<tag>[^\'"]*)            
     
     ((?P<sep2>[\'"])
     (?P<suffix>.*?)
     (?P=sep2))?
     ''', re.VERBOSE | re.MULTILINE)

#Regular expression for finding conditions attributes of the kind $960.a = "14" || $960.a = "22" || $960.a = "41" 
#Used when parsing output formats
pattern_parse_cond_value = re.compile('''
     (\s|\|)*
     (?P<tag>\S*)
     \s*=\s*
     (?P<sep>[\'"])
     (?P<val>.*?)
     (?P=sep)
     ''', re.VERBOSE | re.MULTILINE)

#Regular expression for finding format("a format") function calls in Behaviours actions 
pattern_parse_format_call = re.compile('''
     format\(\s*
     ((?P<sep>[\'"])
     (?P<format>.*?)
     (?P=sep))?
     \s*\)
''', re.VERBOSE | re.MULTILINE)

## def get_migration_status():
##     """
##     Returns the current status of the migration as dictionary.

##     The returned dictionary is in this form:
##     {
##     'kbs':('yes',''),
##     'behaviours':('yes', ''),
##     'formats':('no', 'Formats have not migrated to new Bibformat style'),
##     'udf':('no': 'Bibformat does not support links rules any longer. Please use format elements instead.'),
##     'links':('no', 'Bibformat does not support links rules any longer. Please use format elements instead.'),
##     'extraction':('no', 'Bibformat does not support links rules any longer.'),
##     'file_formats':('no', 'Bibformat does not support links rules any longer.')
##     }
##     """
##     status = {}
##     if old_kbs_exist(): #check kbs status
##         status['kbs'] = ('no', 'Old nowledge bases have not been migrated to new Bibformat knowledge bases')
##     else:
##         status['kbs'] = ('yes', '')
        
##     return status

def migrate_behaviours():
    """
    Migrate the old behaviours to new output formats
    """
    warnings = []
    
    old_behaviours = get_old_behaviours()
    new_behaviours = {}
    #Get all behaviours
    for behaviour_attr in old_behaviours:
        
        #We consider the old name as code (code == of filename)
        name = behaviour_attr[0] #get name
        (filename, code) = get_fresh_output_format_filename(name) #Get a fresh filename for given name
        print name, filename, code
        description = behaviour_attr[2]
        
        add_output_format(code, name, description)
        new_behaviour = ""
        #new_behaviour += "description: %s\n"%description
        
        
        behaviour_conditions = get_old_behaviour_condition(name)
        #Get the associated conditions.
        #The conditions on which we will iterate will maybe need to be split
        #in many conditions, as the new format does not support conditions with
        #multiple arguments
        for cond in behaviour_conditions:
            previous_tag = ""
            add_default_case = True
            evaluation_order = cond[0]
            e_conditions =  extract_cond(cond[1])
            
            #Get the action for these conditions
            #We support only 1 action, and old behaviours usually have 1 action only, so limit to 1st one.
            action = "FIXME"
            behaviour_actions = get_old_behaviour_action(name, evaluation_order)
            
            if len(behaviour_actions) > 0:
                action = behaviour_actions[0]
                evalutation_order = action[0]
                action = extract_action(action[1])
                if len(behaviour_actions) > 1:
                    warnings.append("Too much conditions in rule %s of behaviour %s. Only first one considered." % (evaluation_order, name))
                if action == "FIXME":
                    warnings.append("Too complicated action in rule %s of behaviour %s. Only first one considered." % (evaluation_order, name))
            #Interpret the conditions we have parsed
            for condition in e_conditions:
                if condition.has_key("default"):
                    new_behaviour += "default: %s\n" % action
                    add_default_case = False
                    previous_tag = ""
                elif condition.has_key("value"):
                    tag = condition["tag"]
                    value = condition["value"]
                    if tag != previous_tag:
                        new_behaviour += "tag %s:\n" % tag
                        
                    new_behaviour += '%(value)s --- %(action)s\n' % {'value': value, 'action':action}
                    previous_tag = tag
                #elif condition.has_key("prefix"):
                #    prefix = condition["prefix"]
                #    suffix = condition["suffix"]
                #    tag = condition["tag"]
                #    if tag != previous_tag:
                #        new_behaviour += "tag %s:\n"%tag
                #    if suffix == None:
                #        suffix = ""
                #    if prefix == None:
                #        prefix = ""
                #    new_behaviour += 'template("%(pre)s", "%(suf)s")\n'%{'pre': prefix, 'suf': suffix}
                #    previous_tag = tag
        #Also add the default case, if there was not already here
        if add_default_case:
            new_behaviour += "default: default." + format_template_extension + "\n"
        new_behaviours[filename] = new_behaviour
        
    

    for filename in new_behaviours:
        text = new_behaviours[filename]
        path = outputs_path + os.sep + filename
        f = open(path, 'w')
        f.write(text)
        f.close

    if len(warnings)> 0:
        return '<span style="color: orange;">Migrated with some problems:</span>' + ", ".join(warnings)
    else:
        return '<span style="color: green;">Migrated</span>'
    
def extract_cond(old_cond):
    """
    Returns the parsed condition from the given condition text

    We limit to conditions of the type:
    ""=""
    $960.a = "PICTURE" || $960.a = "22" || ...
    
    """
    conditions_list = []
    cond = {}
    
    if old_cond == '""=""':
        cond['default'] = "action"
        conditions_list.append(cond)
    #elif old_cond.startswith("format_exist("):
    #    match = pattern_parse_format_exist.search(old_cond)
    #    if match != None:
    #        cond['tag'] = translate_tag(match.group("tag"))
    #        cond['prefix'] = match.group("prefix")
    #        cond['suffix'] = match.group("suffix")
    #    conditions_list.append(cond)
    else:
        match_cond_iterator = pattern_parse_cond_value.finditer(old_cond)
        for match in match_cond_iterator:
            cond = {}
            cond['tag'] = translate_tag(match.group('tag'))
            cond['value'] = match.group('val')
            conditions_list.append(cond)
    
    return conditions_list

def extract_action(old_action):
    """
    Returns the action in old_action

    Most actions old old bibformat only call a format.
    Our new 'actions' limit to call of a template
    Then we only look for format("some_format") inside old_action
    """
    match = pattern_parse_format_call.search(old_action)
    if match != None:
        return get_fresh_format_template_filename(match.group("format"))[0] 
    else:
        return "FIXME"

def translate_tag(tag):
    """
    Translate marc code written in the form $250_a.b into 250_a $b
    """
    tag = tag.lstrip("$")
    tag = tag.replace(".", " $")

    return tag
    
def migrate_kbs():
    """
    Migrates the old bibformat kbs to the new bibformat kbs.
    """
    all_old_kbs = get_old_kbs()
    for table in all_old_kbs:
        kb_name = table[0]
        kb_table = table[1]
        kb_description = table[2]
        print "Migrating ", kb_name
        #Note: kb_name was already unique. No risk of creating two tables with same name.
        kb_id = bibformatadminlib.add_kb(kb_name)
        kb_name = get_kb_name(kb_id)
        update_kb_attributes(kb_name, kb_name, kb_description)
        all_old_mappings = get_old_kb_mappings(kb_table)
        for mapping in all_old_mappings:
            key = mapping[0]
            value = mapping[1]
            add_kb_mapping(kb_name, key, value)
            #print "     "+key+" -> "+value
        #This is where we would drop the old table
        #delete_old_kb_table(kb_name)

    #Now this is where we would drop old tables list.
    #delete_old_kbs_list()
    
    return '<span style="color: green;">Migrated</span>'
    
def migrate_formats():
    """
    Migrate old bibformat formats
    We restrict to the creation of file, setting attributes
    and copy old format content into file
    """
    old_formats = get_old_formats()

    for format in old_formats:
        name = format[0]
        description = format[1]
        code = get_old_format(name)

        text = '<name>%s</name>'%name
        text += '<description>%s</description>\n'%description
        #(translated_code, bfe_to_create) = translate_format(code)  #TEMP DISABLED FIXME
        bfe_to_create = [] # TEMP ENABLED FIXME
        #text += translated_code  #TEMP DISABLED FIXME
        text += "<!--ORIGINAL CODE. DON'T FORGET TO REMOVE BEFORE GOING INTO PRODUCTION \n"+code+"-->"
        
        (filename, new_name) = get_fresh_format_template_filename(name)
        path = templates_path + os.sep + filename
        f = open(path, 'w')
        f.write(text)
        f.close
        
    for element in bfe_to_create.keys():
        #Create a predefined content for the element
        text = '''#!/usr/bin/python
# -*- coding: utf-8 -*-
        
def format(bfo, a_parameter="a default value"):
    """
    Created by Migration Kit. Put your comments here.

    @param a_parameter Description for this parameter
    """
    out = ""
    out += bfo.field('%s')
    return out
        '''%bfe_to_create[element]['field']
            
        path = elements_path + os.sep + element + ".py"
        f = open(path, 'w')
        f.write(text)
        f.close
    
    return '<span style="color: red;">Formats Migrated with some problems.</span> Please check manually'


from invenio.bibformat_engine import get_fresh_format_template_filename, get_fresh_output_format_filename
from invenio import bibformatadminlib
from invenio.bibformatadminlib import add_kb_mapping, get_kb_name, update_kb_attributes

if __name__ == "__main__":
    adapt_tables()
    migrate_behaviours()
    migrate_kbs()
    migrate_formats()

