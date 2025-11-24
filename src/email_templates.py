def _default_template(avatarUrl, fullName, htmlContent):
    avatarDiv = '<br>'
    if avatarUrl:
        avatarDiv = f'''<img src="{avatarUrl}" height="80px" width="80px" alt="avatar" title="avatar" style="margin: 20px auto;border-radius: 40px"/>
            <br>
        '''

    fullNameDiv = ''
    if fullName:
        fullNameDiv = f'''<span style="font-weight: bold;font-size: 22px;color: #f3f3f3;margin: 20px 0">{fullName},</span>
            <br>
        '''

    return f"""
    <div style="background: linear-gradient(-20deg, #0a0e10 0%, #ff9b2a 50%, #0a0e10 100%);">
      <div style="margin-left: auto;margin-right: auto;width: 100%;max-width: 600px;padding:40px 0;font-family: Arial, sans-serif">
        <div style="margin: 40px 0;padding: 0 35px 25px;text-align: center;color: #d5d5d5;background: #141617;box-shadow: 3px 3px 10px #000;border: 2px solid #ff9b2a;border-radius: 7px;line-height: 1.3;font-size: 16px;">
    
          {avatarDiv}
          
          {fullNameDiv}
        
          <div class="content">
            {htmlContent}
          </div>
                
          <br>
          <div style="padding: 0;color: #aaa;font-size: 11px;text-align: left;">
            <span>Вы видите это письмо, потому что этот этот адрес указан при регистрации на zovoceana.ru.</span>
            <br>
            <span>С этого электронного адреса будут приходить только важные письма для восстановления пароля, входа в аккаунт и.т.п.</span>
          </div>
        </div>
    
        <div style="padding: 20px 30px;color: #666;overflow: auto;background-color: #00000055;border-radius: 7px">
          <span style="float: left">
            <a href="https://zovoceana.ru" target="_blank" style="font-size: 13px;font-weight: bold;color: #e7e7e7 !important;" rel="noopener noreferrer">zovoceana.ru</a>
            <br>
            <span style="color: #b9b9b9;font-size: 12px;">Сергей Тяпкин</span>
          </span>
        </div>
      </div>
    </div>
    """


def restorePassword(avatarUrl, fullName, code):
    return _default_template(avatarUrl, fullName, f"""
    <span style="color: #d5d5d5">Ваша ссылка для восстановления пароля:</span>
    <br>
    <a href="https://zovoceana.ru/password/restore?code={code}" target="_blank" style="margin-top:10px;line-height: 1;box-sizing: border-box;display: inline-block;max-width: 100%;padding: 10px 15px;border-radius: 5555px;background: #444;border: #1a795f solid 1px;box-shadow: 5px 5px 10px rgb(0 0 0 / 27%);font-weight: bold;color: #b1e5df !important;" rel=" noopener noreferrer"><span style="display: inline-block;width: 14px;height: 18px;vertical-align: middle;"></span> Восстановить пароль</a>
    <br>
    <span style="color: #d5d5d5">Ссылка одноразовая и действительна ровно час</span>    
    """)


def loginByCode(avatarUrl, fullName, code):
    return _default_template(avatarUrl, fullName, f"""
    <span style="color: #d5d5d5">Ваша ссылка для входа:</span>
    <a href="https://zovoceana.ru/login?code={code}" target="_blank" style="margin-top:10px;line-height: 1;box-sizing: border-box;display: inline-block;max-width: 100%;padding: 10px 15px;border-radius: 5555px;background: #444;border: #1a795f solid 1px;box-shadow: 5px 5px 10px rgb(0 0 0 / 27%);font-weight: bold;color: #b1e5df !important;" rel=" noopener noreferrer"><span style="display: inline-block;width: 14px;height: 18px;vertical-align: middle;"></span> Подтвердить регистрацию</a>
    <br>
    <br>
    <span>Ссылка для входа одноразовая и действительна ровно час</span>  
    """)


def confirmEmail(avatarUrl, fullName, code):
    return _default_template(avatarUrl, fullName, f"""
    <span style="color: #d5d5d5">Подтвердите этот адрес, чтобы всегда иметь возможность восстановить аккаунт с его помощью</span>
    <br>
    <br>
    <hr>
    <a href="https://zovoceana.ru/email/confirm?code={code}" target="_blank" style="margin-top:10px;line-height: 1;box-sizing: border-box;display: inline-block;max-width: 100%;padding: 10px 15px;border-radius: 5555px;background: #444;border: #ff9b2a solid 1px;box-shadow: 5px 5px 10px rgb(0 0 0 / 27%);font-weight: bold;color: #ff9b2a !important;" rel=" noopener noreferrer"><span style="display: inline-block;width: 14px;height: 18px;vertical-align: middle;"></span> Подтвердить регистрацию</a>
    <br>
    <br>
    <span>Ссылка для подтверждения одноразовая и действительна ровно день</span>    
    """)
