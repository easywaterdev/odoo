odoo.define('mail_composer_on_send_message.mail_composer_on_send_message', function (require) {

    var ChatterComposer = require('mail.composer.Chatter');

    ChatterComposer.include({
        init: function (parent, model, suggestedPartners, options) {
            // Re-write to always open in full view for messages
            this._super.apply(this, arguments);
            if (! this.options.isLog) {
                this._onOpenFullComposer();
            };
        },
    });

});