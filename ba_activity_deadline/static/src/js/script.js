odoo.define('ba_activity_deadline.alert', function (require) {
    "use strict";

    let Notification = require('web.Notification');
    let session = require('web.session');
    let WebClient = require('web.WebClient');
    let core = require('web.core');
    let date_util = require('web.time');

    let channel = 'ba_activity_deadline.alarm';
    let _t = core._t;

    let ActivityNotification = Notification.extend({
        template: "ba_activity_deadline.notification",

        init: function (parent, params) {
            this._super(parent, params);
            this.aid = params.activityID;
            this.sticky = true;
            this.resModelName = params.resModelName;
            this.resModel = params.resModel;
            this.resID = params.resID;
            this.icon = params.icon;

            this.events = _.extend(this.events || {}, {
                'click .ba_activity_deadline_activity': function () {
                    let self = this;

                    this._rpc({
                        route: '/web/action/load',
                        params: {
                            action_id: 'ba_activity_deadline.action_open_activity',
                        },
                    })
                        .then(function (r) {
                            r.res_id = self.aid;
                            return self.do_action(r);
                        });
                },
                'click .ba_activity_deadline_record': function () {
                    let self = this;

                    this.do_action({
                        type: 'ir.actions.act_window',
                        view_type: 'form',
                        view_mode: 'form',
                        res_model: self.resModel,
                        views: [[false, 'form']],
                        res_id: self.resID,
                        target: 'current',
                    });
                },
                'click .ba_activity_deadline_showed': function () {
                    this.destroy(true);
                },
            });
        },
    });

    WebClient.include({
        start: function () {
            this._super.apply(this, arguments);
            this.call('bus_service', 'addChannel', channel);
            this.call('bus_service', 'startPolling');
            this.call('bus_service', 'onNotification', this, this.onActivityNotif);
        },
        onActivityNotif: function (notifications) {
            let self = this;
            _.each(notifications, function (notification) {
                let ch = notification[0];
                let msg = notification[1];
                if (ch === channel) {
                    self.handlerMsg(msg);
                }
            });
        },

        handlerMsg: function (msg) {
            let self = this;
            if (msg.user_id === session.uid) {
                this._rpc({
                    model: 'mail.activity',
                    method: 'search_read',
                    domain: [['id', '=', msg.id]],
                }).then(function (result) {
                    let title = _t('Activity: ') + result[0].activity_type_id[1];
                    let message = result[0].res_name;
                    let resModel = result[0].res_model;
                    let resModelName = result[0].model_name;
                    let resID = result[0].res_id;
                    let DueDate = date_util.str_to_datetime(result[0].dd);
                    let actCategory = result[0].activity_type_id[0];
                    self._rpc({
                        model: 'mail.activity.type',
                        method: 'search_read',
                        domain: [['id', '=', actCategory]],
                    }).then(function (categ) {
                        let icon = categ[0].icon || 'fa-lightbulb-o';
                        message = '<b>' + resModelName + ': </b>' + message + '<br/>';
                        message += _t('<b>Due Date: </b>') + DueDate;
                        let notificationID = self.call('notification', 'notify', {
                            Notification: ActivityNotification,
                            title: title,
                            message: message,
                            activityID: msg.id,
                            resModel: resModel,
                            resID: resID,
                            resModelName: resModelName,
                            icon: icon,
                        });
                    });
                });
            }
        },
    });

});