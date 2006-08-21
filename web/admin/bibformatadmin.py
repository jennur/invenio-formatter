## $Id$
##
## This file is part of CDS Invenio.
## Copyright (C) 2002, 2003, 2004, 2005, 2006 CERN.
##
## CDS Invenio is free software; you can redistribute it and/or
## modify it under the terms of the GNU General Public License as
## published by the Free Software Foundation; either version 2 of the
## License, or (at your option) any later version.
##
## CDS Invenio is distributed in the hope that it will be useful, but
## WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
## General Public License for more details.  
##
## You should have received a copy of the GNU General Public License
## along with CDS Invenio; if not, write to the Free Software Foundation, Inc.,
## 59 Temple Place, Suite 330, Boston, MA 02111-1307, USA.

"""CDS Invenio BibFormat Administrator Interface."""

__lastupdated__ = """$Date$"""

import MySQLdb

from invenio.bibformatadminlib import *
from invenio.config import cdslang, cdsname
from invenio.bibrankadminlib import check_user
from invenio.webpage import page, create_error_box
from invenio.webuser import getUid, page_not_authorized
from invenio.messages import wash_language, gettext_set_language
from invenio.urlutils import wash_url_argument, redirect_to_url, get_referer
from invenio.search_engine import perform_request_search

__version__ = "$Id$"


def index(req, ln=cdslang):
    """
    Main BibFormat administration page.

    Displays a warning if we find out that etc/biformat dir is not writable by us
    (as most opeation of BibFormat must write in this directory).

    @param ln: language
    """
    warnings = []

    #FIXME Remove when removing Migration Kit
    from invenio.bibformat_migration_kit_assistant_lib import can_write_migration_status_file 
    if not can_write_migration_status_file():
        warnings.append(("WRN_BIBFORMAT_CANNOT_WRITE_MIGRATION_STATUS"))
        
    if not can_write_etc_bibformat_dir():
        warnings.append(("WRN_BIBFORMAT_CANNOT_WRITE_IN_ETC_BIBFORMAT"))
    
    ln = wash_language(ln)
    _ = gettext_set_language(ln)
    
    navtrail = """<a class=navtrail href="%s/admin/index?ln=%s">%s</a>""" % (weburl, ln, _("Admin Area"))
    
    return page(title=_("BibFormat Admin"),
                body=perform_request_index(ln=ln, warnings=warnings),
                language=ln,
                navtrail = navtrail,
                lastupdated=__lastupdated__,
                req=req,
                warnings=warnings)

def output_formats_manage(req, ln=cdslang, sortby="code"):
    """
    Main page for output formats management. Check for authentication and print output formats list.
    @param ln language
    @param sortby the sorting crieteria (can be 'code' or 'name')
    """
    ln = wash_language(ln)
    _ = gettext_set_language(ln)
    navtrail_previous_links = getnavtrail()

    try:
        uid = getUid(req)
    except MySQLdb.Error, e:
        return error_page(req)

    (auth_code, auth_msg) = check_user(uid, 'cfgbibformat')
    if not auth_code:
        sortby = wash_url_argument(sortby, 'str')
        return page(title=_("Manage Output Formats"),
                body=perform_request_output_formats_management(ln=ln, sortby=sortby),
                uid=uid,
                language=ln,
                navtrail = navtrail_previous_links,
                lastupdated=__lastupdated__,
                req=req)   
    else:
        return page_not_authorized(req=req, text=auth_msg, navtrail=navtrail_previous_links)
    
def output_format_show(req, bfo, ln=cdslang, r_fld=[], r_val=[], r_tpl=[], default="", r_upd="", chosen_option="", **args):
    """
    Show a single output format. Check for authentication and print output format settings.

    The page either shows the output format from file, or from user's
    POST session, as we want to let him edit the rules without
    saving. Policy is: r_fld, r_val, rules_tpl are list of attributes
    of the rules.  If they are empty, load from file. Else use
    POST. The i th value of each list is one of the attributes of rule
    i. Rule i is the i th rule in order of evaluation.  All list have
    the same number of item.

    r_upd contains an action that has to be performed on rules. It
    can composed of a number (i, the rule we want to modify) and an
    operator : "save" to save the rules, "add" or "del".
    syntax: operator [number]
    For eg: r_upd = _("Save Changes") saves all rules (no int should be specified).
    For eg: r_upd = _("Add New Rule") adds a rule (no int should be specified).
    For eg: r_upd = _("Remove Rule") + " 5"  deletes rule at position 5.
    The number is used only for operation delete.

    An action can also be in **args. We must look there for string starting
    with '(+|-) [number]' to increase (+) or decrease (-) a rule given by its
    index (number).
    For example "+ 5" increase priority of rule 5 (put it at fourth position).
    The string in **args can be followed by some garbage that looks like .x
    or .y, as this is returned as the coordinate of the click on the
    <input type="image">. We HAVE to use args and reason on its keys, because for <input> of
    type image, iexplorer does not return the value of the tag, but only the name.

    Action is executed only if we are working from user's POST session
    (means we must have loaded the output format first, which is
    totally normal and expected behaviour)

    
    
    @param ln language
    @param bfo the filename of the output format to show
    @param r_fld the list of 'field' attribute for each rule
    @param r_val the list of 'value' attribute for each rule
    @param r_tpl the list of 'template' attribute for each rule
    @param default the default format template used by this output format
    @param r_upd the rule that we want to increase/decrease in order of evaluation
    """
    ln = wash_language(ln)
    _ = gettext_set_language(ln)
    navtrail_previous_links = getnavtrail(''' &gt; <a class=navtrail href="%s/admin/bibformat/bibformatadmin.py/output_formats_manage?ln=%s">%s</a>'''%(weburl, ln, _("Manage Output Formats")))
    code = wash_url_argument(bfo, 'str')
    
    try:
        uid = getUid(req)
    except MySQLdb.Error, e:
        return error_page(req)
     
    (auth_code, auth_msg) = check_user(uid, 'cfgbibformat')
    if not auth_code:
        bfo = wash_url_argument(bfo, 'str')
        default = wash_url_argument(default, 'str')
        r_upd = wash_url_argument(r_upd, 'str')

        if not can_read_output_format(bfo): #No read permission
            return page(title=_("Restricted Output Format"),
                        body = "You don't have permission to view this output format.",
                        language=ln,
                        navtrail = navtrail_previous_links,
                        errors = [("ERR_BIBFORMAT_CANNOT_READ_OUTPUT_FILE", bfo ,"")],
                        lastupdated=__lastupdated__,
                        req=req)
          
        output_format = bibformat_engine.get_output_format(code=bfo, with_attributes=True)
        name = output_format['attrs']['names']['generic']
        if name == "":
            name = bfo
            
        if not can_write_output_format(bfo) and chosen_option == "":#No write permission
            return dialog_box(req=req,
                              ln=ln,
                              title="File Permission on %s"%name,
                              message="You don't have write permission on <i>%s</i>.<br/> You can view the output format, but not edit it."%name,
                              navtrail=navtrail_previous_links,
                              options=[ _("Ok")])

        return page(title=_('Output Format %s Rules'%name),
                    body=perform_request_output_format_show(bfo=bfo, ln=ln, r_fld=r_fld, r_val=r_val, r_tpl=r_tpl, default=default, r_upd=r_upd, args=args),
                    uid=uid,
                    language=ln,
                    navtrail = navtrail_previous_links,
                    lastupdated=__lastupdated__,
                    req=req)   
    else:
        return page_not_authorized(req=req, text=auth_msg, navtrail=navtrail_previous_links)

def output_format_show_attributes(req, bfo, ln=cdslang):
    """
    Page for output format names and descrition attributes edition.
        
    @param ln language
    @param bfo the filename of the template to show 
    """
    ln = wash_language(ln)
    _ = gettext_set_language(ln)
    navtrail_previous_links = getnavtrail(''' &gt; <a class=navtrail href="%s/admin/bibformat/bibformatadmin.py/format_templates_manage?ln=%s">%s</a>'''%(weburl, ln , _("Manage Output Formats")))

    try:
        uid = getUid(req)
    except MySQLdb.Error, e:
        return error_page(req)
    
    (auth_code, auth_msg) = check_user(uid, 'cfgbibformat')
    if not auth_code:
        bfo = wash_url_argument(bfo, 'str')

        if not can_read_output_format(bfo): #No read permission
            return page(title=_("Restricted Output Format"),
                        body = "You don't have permission to view this output format.",
                        language=ln,
                        navtrail = navtrail_previous_links,
                        errors = [("ERR_BIBFORMAT_CANNOT_READ_OUTPUT_FILE", bfo ,"")],
                        lastupdated=__lastupdated__,
                        req=req)
        
        output_format = bibformat_engine.get_output_format(code=bfo, with_attributes=True)
        name = output_format['attrs']['names']['generic']
            
        return page(title=_("Output Format %s Attributes"%name),
                    body=perform_request_output_format_show_attributes(bfo, ln=ln),
                    uid=uid,
                    language=ln,
                    navtrail = navtrail_previous_links ,
                    lastupdated=__lastupdated__,
                    req=req)   

    else:
        return page_not_authorized(req=req, text=auth_msg)

def output_format_show_dependencies(req, bfo, ln=cdslang):
    """
    Show the dependencies of the given output format.
    
    @param ln language
    @param bfo the filename of the output format to show
    """
    ln = wash_language(ln)
    _ = gettext_set_language(ln)
    navtrail_previous_links = getnavtrail(''' &gt; <a class=navtrail href="%s/admin/bibformat/bibformatadmin.py/format_templates_manage?ln=%s">%s</a>'''%(weburl, ln , _("Manage Output Formats")))
    
    try:
        uid = getUid(req)
    except MySQLdb.Error, e:
        return error_page(req)
    
    (auth_code, auth_msg) = check_user(uid, 'cfgbibformat')
    if not auth_code:
        bfo = wash_url_argument(bfo, 'str')

        if not can_read_output_format(bfo): #No read permission
            return page(title=_("Restricted Output Format"),
                        body = "You don't have permission to view this output format.",
                        language=ln,
                        navtrail = navtrail_previous_links,
                        errors = [("ERR_BIBFORMAT_CANNOT_READ_OUTPUT_FILE", bfo ,"")],
                        lastupdated=__lastupdated__,
                        req=req)
        
        format_name = bibformat_engine.get_output_format_attrs(bfo)['names']['generic']

        return page(title=_("Output Format %s Dependencies"%format_name),
                    body=perform_request_output_format_show_dependencies(bfo, ln=ln),
                    uid=uid,
                    language=ln,
                    navtrail = navtrail_previous_links,
                    lastupdated=__lastupdated__,
                    req=req)   

    else:
        return page_not_authorized(req=req, text=auth_msg)

def output_format_update_attributes(req, bfo, ln=cdslang, name = "", description="", code="", content_type="", names_trans=[]):
    """
    Update the name, description and code of given output format
     
    @param ln language
    @param description the new description
    @param name the new name
    @param code the new short code (== new bfo) of the output format
    @param content_type the new content_type of the output format
    @param bfo the filename of the output format to update
    @param names_trans the translations in the same order as the languages from get_languages()
    """
    ln = wash_language(ln)
    _ = gettext_set_language(ln)

    try:
        uid = getUid(req)
    except MySQLdb.Error, e:
        return error_page(req)

    (auth_code, auth_msg) = check_user(uid, 'cfgbibformat')
    if not auth_code:

        name = wash_url_argument(name, 'str')
        description = wash_url_argument(description, 'str')
        bfo = wash_url_argument(bfo, 'str')
        code = wash_url_argument(code, 'str')
        bfo = update_output_format_attributes(bfo, name, description, code, content_type, names_trans)
        
        redirect_to_url(req, "output_format_show?ln=%(ln)s&bfo=%(bfo)s"%{'ln':ln, 'bfo':bfo, 'names_trans':names_trans})
    else:
        return page_not_authorized(req=req, text=auth_msg, chosen_option="")

def output_format_delete(req, bfo, ln=cdslang, chosen_option=""):
    """
    Delete an output format

    @param bfo the filename of the output format to delete
    """
    ln = wash_language(ln)
    _ = gettext_set_language(ln)
    navtrail_previous_links = getnavtrail(''' &gt; <a class=navtrail href="%s/admin/bibformat/bibformatadmin.py/output_formats_manage?ln=%s">%s</a> &gt; %s'''%(weburl, ln, _("Manage Output Formats"), _("Delete Output Format")))
    
    try:
        uid = getUid(req)
    except MySQLdb.Error, e:
        return error_page(req)

    (auth_code, auth_msg) = check_user(uid, 'cfgbibformat')
    if not auth_code:
        
        #Ask confirmation to user if not already done
        chosen_option = wash_url_argument(chosen_option, 'str')
        if chosen_option == "":
            bfo = wash_url_argument(bfo, 'str')
            format_name = bibformat_dblayer.get_output_format_names(bfo)['generic']
            return dialog_box(req=req,
                              ln=ln,
                              title="Delete %s"%format_name,
                              message="Are you sure you want to delete output format <i>%s</i>?" % format_name,
                              navtrail=navtrail_previous_links,
                              options=[_("Cancel"), _("Delete")])
        
        elif chosen_option==_("Delete"):
            delete_output_format(bfo)
        redirect_to_url(req, "output_formats_manage?ln=%(ln)s"%{'ln':ln})
    else:
        return page_not_authorized(req=req, text=auth_msg)
    
def output_format_add(req, ln=cdslang):
    """
    Adds a new output format
    """
    ln = wash_language(ln)
    _ = gettext_set_language(ln)

    try:
        uid = getUid(req)
    except MySQLdb.Error, e:
        return error_page(req)

    (auth_code, auth_msg) = check_user(uid, 'cfgbibformat')
    if not auth_code:

        bfo = add_output_format()
        redirect_to_url(req, "output_format_show_attributes?ln=%(ln)s&bfo=%(bfo)s"%{'ln':ln, 'bfo':bfo})
    else:
        return page_not_authorized(req=req, text=auth_msg)

def format_templates_manage(req, ln=cdslang, checking='0'):
    """
    Main page for formats templates management. Check for authentication and print formats list.
    @param ln language
    @param checking if 0, basic checking. Else perform extensive checking (time-consuming)
    """
    ln = wash_language(ln)
    _ = gettext_set_language(ln)
    navtrail_previous_links = getnavtrail()

    try:
        uid = getUid(req)
    except MySQLdb.Error, e:
        return error_page(req)

    (auth_code, auth_msg) = check_user(uid, 'cfgbibformat')
    if not auth_code:
        checking_level = wash_url_argument(checking, 'int')
        return page(title=_("Manage Format Templates"),
                body=perform_request_format_templates_management(ln=ln, checking=checking_level),
                uid=uid,
                language=ln,
                navtrail = navtrail_previous_links,
                lastupdated=__lastupdated__,
                req=req)   
    else:
        return page_not_authorized(req=req, text=auth_msg, navtrail=navtrail_previous_links)


def format_template_show(req, bft, code=None, ln=cdslang, ln_for_preview=cdslang, pattern_for_preview="", content_type_for_preview="text/html", chosen_option=""):
    """
    Main page for template edition. Check for authentication and print formats editor.
    
    @param ln language
    @param code the code being edited
    @param bft the name of the template to show
    @param ln_for_preview the language for the preview (for bfo)
    @param pattern_for_preview the search pattern to be used for the preview (for bfo)
    @param content_type_for_preview the (MIME) content type of the preview
    @param chosen_option returned value for dialog_box warning
    """
    ln = wash_language(ln)
    _ = gettext_set_language(ln)
        
    navtrail_previous_links = getnavtrail(''' &gt; <a class=navtrail href="%s/admin/bibformat/bibformatadmin.py/format_templates_manage?ln=%s">%s</a>'''%(weburl, ln , _("Manage Format Templates")))

    try:
        uid = getUid(req)
    except MySQLdb.Error, e:
        return error_page(req)

    (auth_code, auth_msg) = check_user(uid, 'cfgbibformat')
    if not auth_code:
        format_template = wash_url_argument(bft, 'str')
        ln_preview = wash_language(ln_for_preview)
        pattern_preview = wash_url_argument(pattern_for_preview, 'str')
        if not can_read_format_template(bft): #No read permission
            return page(title=_("Restricted Format Template"),
                        body = "You don't have permission to view this format template.",
                        language=ln,
                        navtrail = navtrail_previous_links,
                        errors = [("ERR_BIBFORMAT_CANNOT_READ_TEMPLATE_FILE", format_template ,"")],
                        lastupdated=__lastupdated__,
                        req=req)
          
        format_name = bibformat_engine.get_format_template_attrs(bft)['name']
        if not can_write_format_template(bft) and chosen_option == "":#No write permission
            return dialog_box(req=req,
                              ln=ln,
                              title="File Permission on %s"%format_name,
                              message="You don't have write permission on <i>%s</i>.<br/> You can view the template, but not edit it."%format_name,
                              navtrail=navtrail_previous_links,
                              options=[ _("Ok")])
            


        return page(title=_("Format Template %s"%format_name),
                body=perform_request_format_template_show(format_template,
                                                          code=code,
                                                          ln=ln,
                                                          ln_for_preview=ln_preview,
                                                          pattern_for_preview=pattern_preview,
                                                          content_type_for_preview=content_type_for_preview),
                uid=uid,
                language=ln,
                navtrail = navtrail_previous_links,
                lastupdated=__lastupdated__,
                req=req)   
    else:
        return page_not_authorized(req=req, text=auth_msg, navtrail=navtrail_previous_links)

def format_template_show_attributes(req, bft, ln=cdslang):
    """
    Page for template name and descrition attributes edition.
    
    @param ln language
    @param bft the name of the template to show 
    """
    ln = wash_language(ln)
    _ = gettext_set_language(ln)
    navtrail_previous_links = getnavtrail(''' &gt; <a class=navtrail href="%s/admin/bibformat/bibformatadmin.py/format_templates_manage?ln=%s">%s</a>'''%(weburl, ln , _("Manage Format Templates")))

    try:
        uid = getUid(req)
    except MySQLdb.Error, e:
        return error_page(req)
    
    (auth_code, auth_msg) = check_user(uid, 'cfgbibformat')
    if not auth_code:
        format_template = wash_url_argument(bft, 'str')
        format_name = bibformat_engine.get_format_template_attrs(bft)['name']

        if not can_read_format_template(bft): #No read permission
            return page(title=_("Restricted Format Template"),
                        body = "You don't have permission to view this format template.",
                        language=ln,
                        navtrail = navtrail_previous_links,
                        errors = [("ERR_BIBFORMAT_CANNOT_READ_TEMPLATE_FILE", format_template ,"")],
                        lastupdated=__lastupdated__,
                        req=req)
        
        return page(title=_("Format Template %s Attributes"%format_name),
                    body=perform_request_format_template_show_attributes(bft, ln=ln),
                    uid=uid,
                    language=ln,
                    navtrail = navtrail_previous_links ,
                    lastupdated=__lastupdated__,
                    req=req)   

    else:
        return page_not_authorized(req=req, text=auth_msg)

def format_template_show_dependencies(req, bft, ln=cdslang):
    """
    Show the dependencies (on elements) of the given format.
    
    @param ln language
    @param bft the filename of the template to show
    """
    ln = wash_language(ln)
    _ = gettext_set_language(ln)
    navtrail_previous_links = getnavtrail(''' &gt; <a class=navtrail href="%s/admin/bibformat/bibformatadmin.py/format_templates_manage?ln=%s">%s</a>'''%(weburl, ln ,_("Manage Format Templates")))
    
    try:
        uid = getUid(req)
    except MySQLdb.Error, e:
        return error_page(req)
    
    (auth_code, auth_msg) = check_user(uid, 'cfgbibformat')
    if not auth_code:
        format_template = wash_url_argument(bft, 'str')
        format_name = bibformat_engine.get_format_template_attrs(bft)['name']
        
        return page(title=_("Format Template %s Dependencies"%format_name),
                    body=perform_request_format_template_show_dependencies(bft, ln=ln),
                    uid=uid,
                    language=ln,
                    navtrail = navtrail_previous_links,
                    lastupdated=__lastupdated__,
                    req=req)   

    else:
        return page_not_authorized(req=req, text=auth_msg)

def format_template_update_attributes(req, bft, ln=cdslang, name = "", description=""):
    """
    Update the name and description of given format template
     
    @param ln language
    @param description the new description
    @param name the new name
    @param bft the filename of the template to update
    """
    ln = wash_language(ln)
    _ = gettext_set_language(ln)

    try:
        uid = getUid(req)
    except MySQLdb.Error, e:
        return error_page(req)

    (auth_code, auth_msg) = check_user(uid, 'cfgbibformat')
    if not auth_code:

        name = wash_url_argument(name, 'str')
        description = wash_url_argument(description, 'str')
        bft = update_format_template_attributes(bft, name, description)
        
        redirect_to_url(req, "format_template_show?ln=%(ln)s&bft=%(bft)s" % {'ln':ln, 'bft':bft})
    else:
        return page_not_authorized(req=req, text=auth_msg)

def format_template_delete(req, bft, ln=cdslang, chosen_option=""):
    """
    Delete a format template
    """
    ln = wash_language(ln)
    _ = gettext_set_language(ln)
    navtrail_previous_links = getnavtrail(''' &gt; <a class=navtrail href="%s/admin/bibformat/bibformatadmin.py/format_templates_manage?ln=%s">%s</a> &gt; %s'''%(weburl, ln ,_("Manage Format Templates"), _("Delete Format Template")))

    try:
        uid = getUid(req)
    except MySQLdb.Error, e:
        return error_page(req)

    (auth_code, auth_msg) = check_user(uid, 'cfgbibformat')
    if not auth_code:
        #Ask confirmation to user if not already done
        chosen_option = wash_url_argument(chosen_option, 'str')
        if chosen_option == "":
            format_template = wash_url_argument(bft, 'str')
            format_name = bibformat_engine.get_format_template_attrs(bft)['name']
            return dialog_box(req=req,
                              ln=ln,
                              title="Delete %s"%format_name,
                              message="Are you sure you want to delete format template <i>%s</i>?" % format_name,
                              navtrail=navtrail_previous_links,
                              options=[_("Cancel"), _("Delete")])
        
        elif chosen_option==_("Delete"):
            delete_format_template(bft)
            
        redirect_to_url(req, "format_templates_manage?ln=%(ln)s"%{'ln':ln})
    else:
        return page_not_authorized(req=req, text=auth_msg)
    
def format_template_add(req, ln=cdslang):
    """
    Adds a new format template
    """
    ln = wash_language(ln)
    _ = gettext_set_language(ln)

    try:
        uid = getUid(req)
    except MySQLdb.Error, e:
        return error_page(req)

    (auth_code, auth_msg) = check_user(uid, 'cfgbibformat')
    if not auth_code:

        bft = add_format_template()
        redirect_to_url(req, "format_template_show_attributes?ln=%(ln)s&bft=%(bft)s"%{'ln':ln, 'bft':bft})
    else:
        return page_not_authorized(req=req, text=auth_msg)
    
def format_template_show_preview_or_save(req, bft, ln=cdslang, code=None,
                                         ln_for_preview=cdslang, pattern_for_preview="",
                                         content_type_for_preview='text/html',
                                         save_action=None, navtrail=""):
    """
    Print the preview of a record with a format template. To be included inside Format template
    editor. If the save_actiom has a value, then the code should also be saved at the same time

    @param code the code of a template to use for formatting   
    @param ln_for_preview the language for the preview (for bfo)
    @param pattern_for_preview the search pattern to be used for the preview (for bfo)
    @param save_action has a value if the code has to be saved
    @param bft the filename of the template to save
    @param navtrail standard navtrail
    """
    ln = wash_language(ln)
    _ = gettext_set_language(ln)
  
    try:
        uid = getUid(req)
    except MySQLdb.Error, e:
        return error_page(req)

    (auth_code, auth_msg) = check_user(uid, 'cfgbibformat')
    if not auth_code:
        bft = wash_url_argument(bft, 'str')
        if save_action!= None and code != None:
            #save
            update_format_template_code(bft, code=code)
        if code == None:
            code = bibformat_engine.get_format_template(bft)['code']

        ln_for_preview = wash_language(ln_for_preview)
        pattern_for_preview = wash_url_argument(pattern_for_preview, 'str')
        if pattern_for_preview == "":
            recIDs = perform_request_search()
            if len(recIDs) == 0:
                return page(title="No Document Found",
                            body="",
                            uid=uid,
                            language=ln_for_preview,
                            navtrail = "",
                            lastupdated=__lastupdated__,
                            req=req)
            else:
                recID = recIDs[0]
                pattern_for_preview = "recid:%s"%recID
        else:
            recIDs = perform_request_search(p=pattern_for_preview)
            if len(recIDs) == 0:
                return page(title="No Record Found for %s"%pattern_for_preview,
                            body="",
                            uid=uid,
                            language=ln_for_preview,
                            navtrail = "",
                            lastupdated=__lastupdated__,
                            req=req) 
            else:
                recID = recIDs[0]
            
        bfo = bibformat_engine.BibFormatObject(recID, ln_for_preview, pattern_for_preview, None, getUid(req))
        (body, errors) = bibformat_engine.format_with_format_template("", bfo, verbose=7, format_template_code=code)
        
        if content_type_for_preview == 'text/html':
            #Standard page display with CDS headers, etc.
            return page(title="",
                        body=body,
                        uid=uid,
                        language=ln_for_preview,
                        navtrail = navtrail,
                        lastupdated=__lastupdated__,
                        req=req)
        else:
            #Output with chosen content-type.
            req.content_type = content_type_for_preview
            req.send_http_header()
            req.write(body)
    else:
        return page_not_authorized(req=req, text=auth_msg)

def format_template_show_short_doc(req, ln=cdslang, search_doc_pattern=""):
    """
    Prints the format elements documentation in a brief way. To be included inside Format template
    editor.
    
    @param ln: language
    @param search_doc_pattern a search pattern that specified which elements to display
    @param bft the name of the template to show
    """
    ln = wash_language(ln)
    _ = gettext_set_language(ln)
  
    try:
        uid = getUid(req)
    except MySQLdb.Error, e:
        return error_page(req)

    (auth_code, auth_msg) = check_user(uid, 'cfgbibformat')
    if not auth_code:
        search_doc_pattern = wash_url_argument(search_doc_pattern, 'str')
        return perform_request_format_template_show_short_doc(ln=ln, search_doc_pattern=search_doc_pattern)
    else:
        return page_not_authorized(req=req, text=auth_msg)
    
    
def format_elements_doc(req, ln=cdslang):
    """
    Main page for format elements documentation. Check for authentication and print format elements list.
    @param ln language
    """
    ln = wash_language(ln)
    _ = gettext_set_language(ln)
    navtrail_previous_links = getnavtrail()

    try:
        uid = getUid(req)
    except MySQLdb.Error, e:
        return error_page(req)

    (auth_code, auth_msg) = check_user(uid, 'cfgbibformat')
    if not auth_code:
        return page(title=_("Format Elements Documentation"),
                body=perform_request_format_elements_documentation(ln=ln),
                uid=uid,
                language=ln,
                navtrail = navtrail_previous_links,
                lastupdated=__lastupdated__,
                req=req)   
    else:
        return page_not_authorized(req=req, text=auth_msg, navtrail=navtrail_previous_links)

def format_element_show_dependencies(req, bfe, ln=cdslang):
    """
    Shows format element dependencies

    @param bfe the name of the bfe to show
    @param ln language
    """
    ln = wash_language(ln)
    _ = gettext_set_language(ln)
    navtrail_previous_links = getnavtrail(''' &gt; <a class=navtrail href="%s/admin/bibformat/bibformatadmin.py/format_elements_doc?ln=%s">%s</a>'''%(weburl, ln ,_("Format Elements Documentation")))
    try:
        uid = getUid(req)
    except MySQLdb.Error, e:
        return error_page(req)

    (auth_code, auth_msg) = check_user(uid, 'cfgbibformat')
    if not auth_code:
        bfe = wash_url_argument(bfe, 'str')
        return page(title=_("Format Element %s Dependencies"%bfe),
                body=perform_request_format_element_show_dependencies(bfe=bfe, ln=ln),
                uid=uid,
                language=ln,
                navtrail = navtrail_previous_links,
                lastupdated=__lastupdated__,
                req=req)   
    else:
        return page_not_authorized(req=req, text=auth_msg, navtrail=navtrail_previous_links)

def format_element_test(req, bfe, ln=cdslang, param_values=None):
    """
    Allows user to test element with different parameters and check output

    'param_values' is the list of values to pass to 'format'
    function of the element as parameters, in the order ...
    If params is None, this means that they have not be defined by user yet.

    @param bfe the name of the element to test
    @param ln language
    @param param_values the list of parameters to pass to element format function
    """
    ln = wash_language(ln)
    _ = gettext_set_language(ln)
    navtrail_previous_links = getnavtrail(''' &gt; <a class=navtrail href="%s/admin/bibformat/bibformatadmin.py/format_elements_doc?ln=%s">%s</a>'''%(weburl, ln , _("Format Elements Documentation")))
    try:
        uid = getUid(req)
    except MySQLdb.Error, e:
        return error_page(req)

    (auth_code, auth_msg) = check_user(uid, 'cfgbibformat')
    if not auth_code:
        bfe = wash_url_argument(bfe, 'str')
        return page(title=_("Test Format Element %s"%bfe),
                body=perform_request_format_element_test(bfe=bfe, ln=ln, param_values=param_values, uid=getUid(req)),
                uid=uid,
                language=ln,
                navtrail = navtrail_previous_links,
                lastupdated=__lastupdated__,
                req=req)   
    else:
        return page_not_authorized(req=req, text=auth_msg, navtrail=navtrail_previous_links)

def kb_manage(req, ln=cdslang):
    """
    Main page for knowledge bases management. Check for authentication.
    
    @param ln: language
    """
    ln = wash_language(ln)
    _ = gettext_set_language(ln)
    navtrail_previous_links = getnavtrail()

    try:
        uid = getUid(req)
    except MySQLdb.Error, e:
        return error_page(req)

    (auth_code, auth_msg) = check_user(uid, 'cfgbibformat')
    if not auth_code:
        return page(title=_("Manage Knowledge Bases"),
                body=perform_request_knowledge_bases_management(ln=ln),
                uid=uid,
                language=ln,
                navtrail = navtrail_previous_links,
                lastupdated=__lastupdated__,
                req=req)   
    else:
        return page_not_authorized(req=req, text=auth_msg, navtrail=navtrail_previous_links)
    

def kb_show(req, kb, sortby="to", ln=cdslang):
    """
    Shows the content of the given knowledge base id. Check for authentication and kb existence.
    Before displaying the content of the knowledge base, check if a form was submitted asking for
    adding, editing or removing a value.
    
    @param ln language
    @param kb the kb id to show
    @param sortby the sorting criteria ('from' or 'to')
    """
    
    ln = wash_language(ln)
    _ = gettext_set_language(ln)
    navtrail_previous_links = getnavtrail(''' &gt; <a class=navtrail href="%s/admin/bibformat/bibformatadmin.py/kb_manage?ln=%s">%s</a>'''%(weburl, ln, _("Manage Knowledge Bases")))

    try:
        uid = getUid(req)
    except MySQLdb.Error, e:
        return error_page(req)

    (auth_code, auth_msg) = check_user(uid, 'cfgbibformat')
    if not auth_code:
    
        kb_id = wash_url_argument(kb, 'int')
        kb_name = get_kb_name(kb_id)

        if kb_name == None:
            return page(title=_("Unknown Knowledge Base"),
                        body = "",
                        language=ln,
                        navtrail = navtrail_previous_links,
                        errors = [("ERR_BIBFORMAT_KB_ID_UNKNOWN", kb)],
                        lastupdated=__lastupdated__,
                        req=req)


        return page(title=_("Knowledge Base %s"%kb_name),
                body=perform_request_knowledge_base_show(ln=ln, kb_id=kb_id, sortby=sortby),
                uid=uid,
                language=ln,
                navtrail = navtrail_previous_links,
                lastupdated=__lastupdated__,
                req=req)   
    else:
        return page_not_authorized(req=req, text=auth_msg, navtrail=navtrail_previous_links)

def kb_show_attributes(req, kb, ln=cdslang, sortby="to"):
    """
    Shows the attributes (name, description) of a given kb
    
    @param ln language
    @param kb the kb id to show
    @param sortby the sorting criteria ('from' or 'to')
    """
    ln = wash_language(ln)
    _ = gettext_set_language(ln)
    navtrail_previous_links = getnavtrail(''' &gt; <a class=navtrail href="%s/admin/bibformat/bibformatadmin.py/kb_manage?ln=%s">%s</a>'''%(weburl, ln, _("Manage Knowledge Bases")))

    try:
        uid = getUid(req)
    except MySQLdb.Error, e:
        return error_page(req)

    (auth_code, auth_msg) = check_user(uid, 'cfgbibformat')
    if not auth_code:
    
        kb_id = wash_url_argument(kb, 'int')
        kb_name = get_kb_name(kb_id)

        if kb_name == None:
            return page(title=_("Unknown Knowledge Base"),
                        body = "",
                        language=ln,
                        navtrail = navtrail_previous_links,
                        errors = [("ERR_BIBFORMAT_KB_ID_UNKNOWN", kb)],
                        lastupdated=__lastupdated__,
                        req=req)


        return page(title=_("Knowledge Base %s Attributes"%kb_name),
                body=perform_request_knowledge_base_show_attributes(ln=ln, kb_id=kb_id, sortby=sortby),
                uid=uid,
                language=ln,
                navtrail = navtrail_previous_links,
                lastupdated=__lastupdated__,
                req=req)   
    else:
        return page_not_authorized(req=req, text=auth_msg, navtrail=navtrail_previous_links)

def kb_show_dependencies(req, kb, ln=cdslang, sortby="to"):
    """
    Shows the dependencies of a given kb
    
    @param ln language
    @param kb the kb id to show
    @param sortby the sorting criteria ('from' or 'to')
    """
    ln = wash_language(ln)
    _ = gettext_set_language(ln)
    navtrail_previous_links = getnavtrail(''' &gt; <a class=navtrail href="%s/admin/bibformat/bibformatadmin.py/kb_manage?ln=%s">%s</a>'''%(weburl, ln, _("Manage Knowledge Bases")))

    try:
        uid = getUid(req)
    except MySQLdb.Error, e:
        return error_page(req)

    (auth_code, auth_msg) = check_user(uid, 'cfgbibformat')
    if not auth_code:
    
        kb_id = wash_url_argument(kb, 'int')
        kb_name = get_kb_name(kb_id)

        if kb_name == None:
            return page(title=_("Unknown Knowledge Base"),
                        body = "",
                        language=ln,
                        navtrail = navtrail_previous_links,
                        errors = [("ERR_BIBFORMAT_KB_ID_UNKNOWN", kb)],
                        lastupdated=__lastupdated__,
                        req=req)


        return page(title=_("Knowledge Base %s Dependencies"%kb_name),
                body=perform_request_knowledge_base_show_dependencies(ln=ln, kb_id=kb_id, sortby=sortby),
                uid=uid,
                language=ln,
                navtrail = navtrail_previous_links,
                lastupdated=__lastupdated__,
                req=req)   
    else:
        return page_not_authorized(req=req, text=auth_msg, navtrail=navtrail_previous_links)
    
def kb_add_mapping(req, kb, mapFrom, mapTo, sortby="to", ln=cdslang):
    """
    Adds a new mapping to a kb.
    
    @param ln language
    @param kb the kb id to show
    @param sortby the sorting criteria ('from' or 'to')
    """
    ln = wash_language(ln)
    _ = gettext_set_language(ln)
    navtrail_previous_links = getnavtrail(''' &gt; <a class=navtrail href="%s/admin/bibformat/bibformatadmin.py/kb_manage?ln=%s">%s</a>'''%(weburl, ln, _("Manage Knowledge Bases")))
    
    try:
        uid = getUid(req)
    except MySQLdb.Error, e:
        return error_page(req)

    (auth_code, auth_msg) = check_user(uid, 'cfgbibformat')
    if not auth_code:

        kb_id = wash_url_argument(kb, 'int')
        kb_name = get_kb_name(kb_id)
   
        if kb_name == None:
            return page(title=_("Unknown Knowledge Base"),
                        body = "",
                        language=ln,
                        navtrail = navtrail_previous_links,
                        errors = [("ERR_BIBFORMAT_KB_ID_UNKNOWN", kb)],
                        lastupdated=__lastupdated__,
                        req=req)


    
        key = wash_url_argument(mapFrom, 'str')
        value = wash_url_argument(mapTo, 'str')
        
        add_kb_mapping(kb_name, key, value)
        redirect_to_url(req, "kb_show?ln=%(ln)s&kb=%(kb)s&sortby=%(sortby)s"%{'ln':ln, 'kb':kb_id, 'sortby':sortby})
    else:
        return page_not_authorized(req=req, text=auth_msg, navtrail=navtrail_previous_links)

def kb_edit_mapping(req, kb, key, mapFrom, mapTo, update="", delete="", sortby="to", ln=cdslang):
    """
    Edit a mapping to in kb. Edit can be "update old value" or "delete existing value"

    @param kb the knowledge base id to edit
    @param key the key of the mapping that will be modified
    @param mapFrom the new key of the mapping
    @param mapTo the new value of the mapping
    @param update contains a value if the mapping is to be updated
    @param delete contains a value if the mapping is to be deleted
    @param sortby the sorting criteria ('from' or 'to')
    """
    ln = wash_language(ln)
    _ = gettext_set_language(ln)
    navtrail_previous_links = getnavtrail(''' &gt; <a class=navtrail href="%s/admin/bibformat/bibformatadmin.py/kb_manage?ln=%s">%s</a>'''%(weburl, ln, _("Manage Knowledge Bases")))
    
    try:
        uid = getUid(req)
    except MySQLdb.Error, e:
        return error_page(req)

    (auth_code, auth_msg) = check_user(uid, 'cfgbibformat')
    if not auth_code:
        kb_id = wash_url_argument(kb, 'int')
        kb_name = get_kb_name(kb_id)
   
        if kb_name == None:
            return page(title=_("Unknown Knowledge Base"),
                        body = "",
                        language=ln,
                        navtrail = navtrail_previous_links,
                        errors = [("ERR_BIBFORMAT_KB_ID_UNKNOWN", kb)],
                        lastupdated=__lastupdated__,
                        req=req)

        
        key = wash_url_argument(key, 'str')
        if delete != "":
            #Delete
            remove_kb_mapping(kb_name, key)
        else:
            #Update
            new_key = wash_url_argument(mapFrom, 'str')
            new_value = wash_url_argument(mapTo, 'str')
            update_kb_mapping(kb_name, key, new_key, new_value)

        redirect_to_url(req, "kb_show?ln=%(ln)s&kb=%(kb)s&sortby=%(sortby)s"%{'ln':ln, 'kb':kb_id, 'sortby':sortby})
    else:
        return page_not_authorized(req=req, text=auth_msg, navtrail=navtrail_previous_links)

def kb_update_attributes(req, kb, name, description, sortby="to", ln=cdslang):
    """
    Update the attributes of the kb
    
    @param ln language
    @param kb the kb id to update
    @param sortby the sorting criteria ('from' or 'to')
    @param name the new name of the kn
    @param description the new description of the kb
    """
    ln = wash_language(ln)
    _ = gettext_set_language(ln)

    navtrail_previous_links = getnavtrail(''' &gt; <a class=navtrail href="%s/admin/bibformat/bibformatadmin.py/kb_manage?ln=%s">%s</a>'''%(weburl, ln, _("Manage Knowledge Bases")))
    
    try:
        uid = getUid(req)
    except MySQLdb.Error, e:
        return error_page(req)

    (auth_code, auth_msg) = check_user(uid, 'cfgbibformat')
    if not auth_code:
        kb_id = wash_url_argument(kb, 'int')
        kb_name = get_kb_name(kb_id)

        if kb_name == None:
            return page(title=_("Unknown Knowledge Base"),
                        body = "",
                        language=ln,
                        navtrail = navtrail_previous_links,
                        errors = [("ERR_BIBFORMAT_KB_ID_UNKNOWN", kb)],
                        lastupdated=__lastupdated__,
                        req=req)

        new_name = wash_url_argument(name, 'str')
        new_desc = wash_url_argument(description, 'str')
        update_kb_attributes(kb_name, new_name, new_desc)
        redirect_to_url(req, "kb_show?ln=%(ln)s&kb=%(kb)s&sortby=%(sortby)s"%{'ln':ln, 'kb':kb_id, 'sortby':sortby})
    else:
        return page_not_authorized(req=req, text=auth_msg, navtrail=navtrail_previous_links)
    
def kb_add(req, ln=cdslang, sortby="to"):
    """
    Adds a new kb
    """
    ln = wash_language(ln)
    _ = gettext_set_language(ln)
    navtrail_previous_links = getnavtrail(''' &gt; <a class=navtrail href="%s/admin/bibformat/bibformatadmin.py/kb_manage?ln=%s">%s</a>'''%(weburl, ln, _("Manage Knowledge Bases")))

    try:
        uid = getUid(req)
    except MySQLdb.Error, e:
        return error_page(req)

    (auth_code, auth_msg) = check_user(uid, 'cfgbibformat')
    if not auth_code:
        kb_id = add_kb()
        redirect_to_url(req, "kb_show_attributes?ln=%(ln)s&kb=%(kb)s"%{'ln':ln, 'kb':kb_id, 'sortby':sortby})
    else:
        navtrail_previous_links = getnavtrail(''' &gt; <a class=navtrail href="%s/admin/bibformat/bibformatadmin.py/kb_manage?ln=%s">%s</a>'''%(weburl, ln, _("Manage Knowledge Bases")))
    
        return page_not_authorized(req=req, text=auth_msg, navtrail=navtrail_previous_links)
    

def kb_delete(req, kb, ln=cdslang, chosen_option="", sortby="to"):
    """
    Deletes an existing kb

    @param kb the kb id to delete
    """
    ln = wash_language(ln)
    _ = gettext_set_language(ln)
    navtrail_previous_links = getnavtrail(''' &gt; <a class=navtrail href="%s/admin/bibformat/bibformatadmin.py/kb_manage?ln=%s">%s</a> &gt; %s'''%(weburl, ln, _("Manage Knowledge Bases"), _("Delete Knowledge Base")))

    try:
        uid = getUid(req)
    except MySQLdb.Error, e:
        return error_page(req)

    (auth_code, auth_msg) = check_user(uid, 'cfgbibformat')
    if not auth_code:
        kb_id = wash_url_argument(kb, 'int')
        kb_name = get_kb_name(kb_id)
        if kb_name == None:
            return page(title=_("Unknown Knowledge Base"),
                        body = "",
                        language=ln,
                        navtrail = navtrail_previous_links,
                        errors = [("ERR_BIBFORMAT_KB_ID_UNKNOWN", kb)],
                        lastupdated=__lastupdated__,
                        req=req)

        #Ask confirmation to user if not already done
        chosen_option = wash_url_argument(chosen_option, 'str')
        if chosen_option == "":
            return dialog_box(req=req,
                              ln=ln,
                              title="Delete %s"%kb_name,
                              message="Are you sure you want to delete knowledge base <i>%s</i>?" % kb_name,
                              navtrail=navtrail_previous_links,
                              options=[_("Cancel"), _("Delete")])
        
        elif chosen_option==_("Delete"):
            delete_kb(kb_name)
            
        redirect_to_url(req, "kb_manage?ln=%(ln)s"%{'ln':ln})
    else:
        navtrail_previous_links = getnavtrail(''' &gt; <a class=navtrail href="%s/admin/bibformat/bibformatadmin.py/kb_manage">%s</a>'''%(weburl, _("Manage Knowledge Bases")))
    
        return page_not_authorized(req=req, text=auth_msg, navtrail=navtrail_previous_links)

def validate_format(req, ln=cdslang, bfo=None, bft=None, bfe=None):
    """
    Returns a page showing the status of an output format or format
    template or format element. This page is called from output
    formats management page or format template management page or
    format elements documentation.

    The page only shows the status of one of the format, depending on
    the specified one. If multiple are specified, shows the first one.

    @param ln language
    @param bfo an output format 6 chars code
    @param bft a format element filename
    @param bfe a format element name
    """
    ln = wash_language(ln)
    _ = gettext_set_language(ln)


    try:
        uid = getUid(req)
    except MySQLdb.Error, e:
        return error_page(req)

    (auth_code, auth_msg) = check_user(uid, 'cfgbibformat')
    if not auth_code:
        if bfo != None: #Output format validation
            bfo = wash_url_argument(bfo, 'str')
            navtrail_previous_links = getnavtrail(''' &gt; <a class=navtrail href="%s/admin/bibformat/bibformatadmin.py/output_formats_manage?ln=%s">%s</a>'''%(weburl, ln, _("Manage Output Formats")))
            
            if not can_read_output_format(bfo): #No read permission
                return page(title=_("Restricted Output Format"),
                            body = "You don't have permission to view this output format.",
                            language=ln,
                            navtrail = navtrail_previous_links,
                            errors = [("ERR_BIBFORMAT_CANNOT_READ_OUTPUT_FILE", bfo ,"")],
                            lastupdated=__lastupdated__,
                            req=req)
        
            output_format = bibformat_engine.get_output_format(code=bfo, with_attributes=True)
            name = output_format['attrs']['names']['generic']
            title = _("Validation of Output Format %s"%name)
            
        elif bft != None: #Format template validation
            bft = wash_url_argument(bft, 'str')
            navtrail_previous_links = getnavtrail(''' &gt; <a class=navtrail href="%s/admin/bibformat/bibformatadmin.py/format_templates_manage?ln=%s">%s</a>'''%(weburl, ln, _("Manage Format Templates")))
            
            if not can_read_format_template(bft): #No read permission
                return page(title=_("Restricted Format Template"),
                            body = "You don't have permission to view this format template.",
                            language=ln,
                            navtrail = navtrail_previous_links,
                            errors = [("ERR_BIBFORMAT_CANNOT_READ_TEMPLATE_FILE", bft ,"")],
                            lastupdated=__lastupdated__,
                            req=req)
            name = bibformat_engine.get_format_template_attrs(bft)['name']
            title = _("Validation of Format Template %s"%name)
            
        elif bfe != None: #Format element validation
            bfe = wash_url_argument(bfe, 'str')
            navtrail_previous_links = getnavtrail(''' &gt; <a class=navtrail href="%s/admin/bibformat/bibformatadmin.py/format_elements_doc?ln=%s#%s">%s</a>'''%(weburl,ln , bfe.upper() ,_("Format Elements Documentation")))
            
            if not can_read_format_element(bfe) and not bibformat_dblayer.tag_exists_for_name(bfe): #No read permission
                return page(title=_("Restricted Format Element"),
                            body = "You don't have permission to view this format element.",
                            language=ln,
                            navtrail = navtrail_previous_links,
                            errors = [("ERR_BIBFORMAT_CANNOT_READ_ELEMENT_FILE", bfe ,"")],
                            lastupdated=__lastupdated__,
                            req=req)
            title = _("Validation of Format Element %s"%bfe)

        else: #No format specified
            return page(title=_("Format Validation"),
                        uid=uid,
                        language=ln,
                        errors = [("ERR_BIBFORMAT_VALIDATE_NO_FORMAT")],
                        navtrail = navtrail_previous_links,
                        lastupdated=__lastupdated__,
                        req=req)       

        return page(title=title,
                    body=perform_request_format_validate(ln=ln, bfo=bfo, bft=bft, bfe=bfe),
                    uid=uid,
                    language=ln,
                    navtrail = navtrail_previous_links,
                    lastupdated=__lastupdated__,
                    req=req) 

    else:
        navtrail_previous_links = getnavtrail(''' &gt; <a class=navtrail href="%s/admin/bibformat/bibformatadmin.py/?ln=%s'''%(weburl, ln))
        
        return page_not_authorized(req=req, text=auth_msg, navtrail=navtrail_previous_links)

def dialog_box(req, url="", ln=cdslang, navtrail="", title="", message="", options=[]):
    """
    Returns a dialog box with a given title, message and options.
    Used for asking confirmation on actions.

    The page that will receive the result must take 'chosen_option' as parameter.
    
    @param url the url used to submit the options chosen by the user
    @param options the list of labels for the buttons given as choice to user
    """
    bibformat_templates = invenio.template.load('bibformat')

    return page(title="",
                body = bibformat_templates.tmpl_admin_dialog_box(url, ln, title, message, options),
                language=ln,
                lastupdated=__lastupdated__,
                navtrail=navtrail,
                req=req)

def error_page(req):
    """
    Returns a default error page
    """
    return page(title="Internal Error",
                body = create_error_box(req, ln=cdslang),
                description="%s - Internal Error" % cdsname, 
                keywords="%s, CDS Invenio, Internal Error" % cdsname,
                language=cdslang)