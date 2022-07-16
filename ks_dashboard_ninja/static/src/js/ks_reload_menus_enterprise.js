odoo.define('ks_dashboard_ninja.ksMenus', function (require) {
    "use strict";

    var core = require('web.core');
    var ajax = require('web.ajax');
    var QWeb = core.qweb;
    var session = require('web.session');
    var Dialog = require('web.Dialog');
    var fieldUtils = require('web.field_utils');
    var AbstractAction = require('web.AbstractAction');
    var ListControllerEnterPrise = require('web.ListController');
    var framework = require('web.framework');
    var view_registry = require('web.view_registry');
    var dom = require('web.dom');
    var ListView = require('web.ListView');
    var FormController =require('web.FormController');
    var _t = core._t;
    const { bus } = require('web.core');
    const WebClient = require('web.WebClient');


    WebClient.include({
        events: _.extend({}, WebClient.prototype.events, {
        'ks_reload_menu_data_enterprise': '_ksonReloadMenuDataEnterprise',
        }),
        custom_events: _.extend({}, WebClient.prototype.custom_events, {
        'ks_reload_menu_data_enterprise': '_ksonReloadMenuDataEnterprise',
    }),
        _ksonReloadMenuDataEnterprise: async function (ev={}) {

            var current_primary_menu =0;
            if ('ks_menu' in ev.data){
                current_primary_menu = ev.data.ks_menu
            }
            else{
                current_primary_menu = this.menu.current_primary_menu;
            }

            bus.trigger('clear_cache');
            const menuData = await this.load_menus();

            await this._ksreinstanciateMenuEnterprise(menuData);
            this.menu.change_menu_section(current_primary_menu);
        },

        _ksreinstanciateMenuEnterprise: async function (newMenuData) {
             const oldMenu = this.menu;
             this.menu = await this._instanciateMenu(newMenuData);
             await this.menu.appendTo(document.createDocumentFragment());
             this.menu.toggle_mode(this.homeMenuManagerDisplayed, false);
             dom.prepend(this.$el, this.menu.$el, {
                    callbacks: [{ widget: this.menu }],
                    in_DOM: true,
             });

             if (oldMenu) {
                 oldMenu.destroy();
             }

             this.el.prepend(this.menu.el);

        },

    });

});


