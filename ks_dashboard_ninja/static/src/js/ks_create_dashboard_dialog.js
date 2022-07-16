odoo.define('ks_dashboard_ninja.kscontroller', function (require) {
    "use strict";

    var core = require('web.core');
    var ajax = require('web.ajax');
    var QWeb = core.qweb;
    var session = require('web.session');
    var Dialog = require('web.Dialog');
    var fieldUtils = require('web.field_utils');
    var AbstractAction = require('web.AbstractAction');
    var ListController = require('web.ListController');
    var framework = require('web.framework');
    var view_registry = require('web.view_registry');
    var dom = require('web.dom');
    var ListView = require('web.ListView');
    var FormController =require('web.FormController');
    var _t = core._t;
    const { bus } = require('web.core');
    const WebClient = require('web.WebClient');
    const ksMenus = require('web.Menu');
    var ListView = require('web.ListRenderer');


    WebClient.include({
        events: _.extend({}, WebClient.prototype.events, {
        'ks_reload_menu_data': '_ksonReloadMenuData',
        }),
        custom_events: _.extend({}, WebClient.prototype.custom_events, {
        'ks_reload_menu_data': '_ksonReloadMenuData',
    }),
        _ksonReloadMenuData: async function (ev={}) {
            var current_primary_menu =0;
            if ('ks_menu' in ev.data){
                current_primary_menu = ev.data.ks_menu
            }
            else{
                current_primary_menu = this.menu.current_primary_menu;
            }

            bus.trigger('clear_cache');
            const menuData = await this.load_menus();

            await this._ksreinstanciateMenu(menuData);
            this.menu.change_menu_section(current_primary_menu);
    },

        _ksreinstanciateMenu: async function (newMenuData) {
            const oldMenu = this.menu;
            this.menu = new ksMenus(this, newMenuData)
            await this.menu.appendTo(document.createDocumentFragment());
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

    return ListController;
});