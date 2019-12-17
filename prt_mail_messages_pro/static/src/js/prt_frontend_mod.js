odoo.define('prt_mail_messages_pro.mail_settings_widget_extend', function (require) {
"use strict";

var Activity = require('mail.Activity');
var AttachmentBox = require('mail.AttachmentBox');
var ChatterComposer = require('mail.composer.Chatter');
var Followers = require('mail.Followers');
var ThreadField = require('mail.ThreadField');
var mailUtils = require('mail.utils');

var concurrency = require('web.concurrency');
var config = require('web.config');
var core = require('web.core');

var QWeb = core.qweb;
var ChatThread = require('mail.widget.Thread');
var Chatter = require('mail.Chatter');
var _t = core._t;
var time = require('web.time');
var rpc = require('web.rpc');
var DocumentViewer = require('mail.DocumentViewer');
var mailUtils = require('mail.utils');

var ORDER = {
    ASC: 1,
    DESC: -1,
};

    Chatter.include({
        //action by click
        events: {
            'click .o_chatter_button_new_message': '_onOpenComposerMessage',
            'click .o_chatter_button_log_note': '_onOpenComposerNote',
            'click .o_chatter_button_attachment': '_onClickAttachmentButton',
            'click .o_chatter_button_schedule_activity': '_onScheduleActivity',
            'click .o_filter_checkbox': '_update',
        },
        // public
        //read from DB from go record to record and NOT run start function
        update: function (record, fieldNames) {
            var self = this;
            if (typeof this.fields.thread !== typeof undefined && this.fields.thread !== false){
              if (this.fields.thread.model) {
                if (this.record.res_id !== record.res_id && typeof record.res_id !== typeof undefined && record.res_id !== false) {
                    this.fields.thread.res_id = record.res_id;
                    rpc.query({
                                model: this.fields.thread.model,
                                method: 'read_sudo',
                                args: [[this.fields.thread.res_id], ['hide_notifications']],

                            }).then(function(result){

                                if (result[0].hide_notifications){
                                    self.$('.o_filter_checkbox').prop("checked", true );
                                    _.extend(self.fields.thread._threadWidget._disabledOptions, {filter: 'yes',});
                                }
                                else{
                                    self.$('.o_filter_checkbox').prop( "checked", false );
                                    _.extend(self.fields.thread._threadWidget._disabledOptions, {filter: 'no',});
                                }
                            });
                }
              }
            };
            this._super.apply(this, arguments);
        },
        //read from DB field hide_notifications and change checkbox and reload message
        start: function () {
            var res = this._super.apply(this, arguments);
            var self = this;

            if (typeof this.fields.thread !== typeof undefined && this.fields.thread !== false){
              if (typeof this.fields.thread.res_id !== typeof undefined && this.fields.thread.res_id !== false) {
              rpc.query({
                          model: this.fields.thread.model,
                          method: 'read_sudo',
                          args: [[this.fields.thread.res_id], ['hide_notifications']],

                      }).then(function(result){
                          if (result[0].hide_notifications){
                              self.$('.o_filter_checkbox').prop( "checked", true );
                              _.extend(self.fields.thread._threadWidget._disabledOptions, {filter: 'yes',});
                          }
                          else{
                              self.$('.o_filter_checkbox').prop( "checked", false );
                              _.extend(self.fields.thread._threadWidget._disabledOptions, {filter: 'no',});
                          }
                          self.trigger_up('reload');
                          //self.update(self.fields.thread.record);
                          });
                        };
                      };
            return res;
        },


        //Write to current model status checkbox and reload message (filtered)
        _update: function () {
            var check = false
            if (this.$('.o_filter_checkbox')[0].checked) {
                _.extend(this.fields.thread._threadWidget._disabledOptions, {filter: 'yes',});
                check = true
            }
            else
                _.extend(this.fields.thread._threadWidget._disabledOptions, {filter: 'no',});

            rpc.query({
                        model: this.fields.thread.model,
                        method: 'write_sudo',
                        args: [[this.fields.thread.res_id], {
                                hide_notifications: check,
            },],
                    })
            this.update(this.fields.thread.record);
         },
    });


    ChatThread.include({

      events: {
        'click a': '_onClickRedirect',
        'click img': '_onClickRedirect',
        'click strong': '_onClickRedirect',
        'click .o_thread_show_more': '_onClickShowMore',
        'click .o_attachment_download': '_onAttachmentDownload',
        'click .o_attachment_view': '_onAttachmentView',
        'click .o_thread_message_needaction': '_onClickMessageNeedaction',
        'click .o_thread_message_star': '_onClickMessageStar',
        'click .o_thread_message_reply': '_onClickMessageReply',
        'click .oe_mail_expand': '_onClickMailExpand',
        'click .o_thread_message': '_onClickMessage',
        'click': '_onClick',
        'click .o_thread_message_email_exception': '_onClickEmailException',
        'click .o_thread_message_email_bounce': '_onClickEmailException',
        'click .o_thread_message_moderation': '_onClickMessageModeration',
        'change .moderation_checkbox': '_onChangeModerationCheckbox',

          "click .o_thread_message_reply_composer_quote": function (event) {
              event.stopPropagation();
              var message_id = $(event.currentTarget).data('message-id');
              this.reply_composer('quote', message_id);
          },
          "click .o_thread_message_reply_composer_forward": function (event) {
              event.stopPropagation();
              var message_id = $(event.currentTarget).data('message-id');
              this.reply_composer('forward', message_id);
          },
          "click .o_thread_message_reply_composer_move": function (event) {
              event.stopPropagation();
              var message_id = $(event.currentTarget).data('message-id');
              this.move_composer(message_id);
          },
          "click .o_thread_message_reply_composer_delete": function (event) {
              event.stopPropagation();
              if (confirm(_t("Message will be deleted! Continue?"))) {
                var message_id = $(event.currentTarget).data('message-id');
                var self = this;
                rpc.query({
                      model: 'mail.message',
                      method: 'unlink',
                      args: [[message_id]],
                    }).then(function(result){
                        self.trigger_up('reload');
                    });
              }
          },
      },

      // Reply or Quote
      reply_composer: function(wiz_mode, message_id) {
            var self = this;
            rpc.query({
              model: 'mail.message',
              method: 'reply_prep_context',
              args: [[message_id]],
              context: {wizard_mode:wiz_mode}
            }).then(function(result){
              var action = {
                  type: 'ir.actions.act_window',
                  res_model: 'mail.compose.message',
                  view_mode: 'form',
                  view_type: 'form',
                  views: [[false, 'form']],
                  target: 'new',
                  context: result,
              };
              self.do_action(action, {
                  on_close: function close_dlg()
                  {
                    self.trigger_up('reload');
                  }
                   });
                 })
      },

      // Move
      move_composer: function(message_id) {
            var self = this;
            var action = {
                type: 'ir.actions.act_window',
                res_model: 'prt.message.move.wiz',
                view_mode: 'form',
                view_type: 'form',
                views: [[false, 'form']],
                target: 'new',
                context: {thread_message_id:message_id},
            };
            self.do_action(action, {
                on_close: function close_move() {
                  self.trigger_up('reload');}
                  }
            );
      },

    render: function (thread, options) {
        var self = this;
        var shouldScrollToBottomAfterRendering = false;
        if (this._currentThreadID === thread.getID() && this.isAtBottom()) {
            shouldScrollToBottomAfterRendering = true;
        }
        this._currentThreadID = thread.getID();

        // copy so that reverse do not alter order in the thread object
        var messages = _.clone(thread.getMessages({ domain: options.domain || []}));
        var message_ids = thread._messageIDs;

        // Remove message if id is not in messageIDs
        // Used to handle moved messages
        if (typeof message_ids !== typeof undefined && message_ids !== false) {
          for (var i = 0; i < messages.length; i++) {
            if (message_ids.indexOf(messages[i]._id) == -1) {
              messages.splice(i, 1);
            }
          }
        }

        var modeOptions = options.isCreateMode ? this._disabledOptions :
                                                 this._enabledOptions;

        // attachments ordered by messages order (increasing ID)
        this.attachments = _.uniq(_.flatten(_.map(messages, function (message) {
            return message.getAttachments();
        })));

        options = _.extend({}, modeOptions, options, {
            selectedMessageID: this._selectedMessageID,
        });

        // dict where key is message ID, and value is whether it should display
        // the author of message or not visually
        var displayAuthorMessages = {};

        // Hide avatar and info of a message if that message and the previous
        // one are both comments wrote by the same author at the same minute
        // and in the same document (users can now post message in documents
        // directly from a channel that follows it)
        var prevMessage;
        _.each(messages, function (message) {
            if (
                // is first message of thread
                !prevMessage ||
                // more than 1 min. elasped
                (Math.abs(message.getDate().diff(prevMessage.getDate())) > 60000) ||
                prevMessage.getType() !== 'comment' ||
                message.getType() !== 'comment' ||
                // from a different author
                (prevMessage.getAuthorID() !== message.getAuthorID()) ||
                (
                    // messages are linked to a document thread
                    (
                        prevMessage.isLinkedToDocumentThread() &&
                        message.isLinkedToDocumentThread()
                    ) &&
                    (
                        // are from different documents
                        prevMessage.getDocumentModel() !== message.getDocumentModel() ||
                        prevMessage.getDocumentID() !== message.getDocumentID()
                    )
                )
            ) {
                displayAuthorMessages[message.getID()] = true;
            } else {
                displayAuthorMessages[message.getID()] = !options.squashCloseMessages;
            }
            prevMessage = message;
        });

        if (self._disabledOptions.filter == 'yes') {
            messages = _.filter(messages, function(msg){ return (msg._type != "notification"  ); });
        }

        if (modeOptions.displayOrder === ORDER.ASC) {
            messages.reverse();
        }



        this.$el.html(QWeb.render('mail.widget.Thread', {
            thread: thread,
            displayAuthorMessages: displayAuthorMessages,
            options: options,
            ORDER: ORDER,
            //my
            messages: messages,
            dateFormat: time.getLangDatetimeFormat(),
        }));

        // must be after mail.widget.Thread rendering, so that there is the
        // DOM element for the 'is typing' notification bar
        if (thread.hasTypingNotification()) {
            this.renderTypingNotificationBar(thread);
        }

        _.each(messages, function (message) {
            var $message = self.$('.o_thread_message[data-message-id="'+ message.getID() +'"]');
            $message.find('.o_mail_timestamp').data('date', message.getDate());




            self._insertReadMore($message);
        });

        if (shouldScrollToBottomAfterRendering) {
            this.scrollToBottom();
        }

        if (!this._updateTimestampsInterval) {
            this.updateTimestampsInterval = setInterval(function () {
                self._updateTimestamps();
            }, 1000*60);
        }

        this._renderMessageMailPopover(messages);
    },

    });
});
