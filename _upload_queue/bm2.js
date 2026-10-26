(async function(){
  if(window.__skhRunning){alert('已在运行中');return;}
  window.__skhRunning=true;
  const sleep=ms=>new Promise(r=>setTimeout(r,ms));
  const BASE='https://api.skillhub.cn/api/v1/orgs/3839';
  // 悬浮日志窗
  const box=document.createElement('div');
  box.style.cssText='position:fixed;top:10px;right:10px;z-index:999999;background:#1e1e2e;color:#a6e3a1;padding:12px;border-radius:8px;font:12px monospace;max-height:70vh;overflow:auto;width:360px;white-space:pre-wrap;box-shadow:0 4px 20px rgba(0,0,0,.5)';
  document.body.appendChild(box);
  const log=t=>{box.textContent+=t+'\n';box.scrollTop=box.scrollHeight;};
  log('▶ SkillHub 一键任务启动');
  try{
    const LIST=[{"slug": "hernia-aftercare-tianbao", "name": "疝气术后护理", "category": "life-service"}, {"slug": "thyroid-nodule-aftercare-tianbao", "name": "甲状腺结节术后", "category": "life-service"}, {"slug": "gout-diet-taboo-tianbao", "name": "痛风饮食禁忌", "category": "life-service"}, {"slug": "anemia-diet-tianbao", "name": "贫血食疗", "category": "life-service"}, {"slug": "osteoporosis-diet-tianbao", "name": "骨质疏松饮食", "category": "life-service"}, {"slug": "folic-acid-supplement-tianbao", "name": "叶酸补充须知", "category": "life-service"}, {"slug": "contraception-comparison-tianbao", "name": "避孕方式对比", "category": "life-service"}, {"slug": "male-health-checkup-tianbao", "name": "男科检查项目", "category": "life-service"}, {"slug": "student-archive-keep-tianbao", "name": "学籍档案存放", "category": "life-service"}, {"slug": "student-grant-apply-tianbao", "name": "贫困生助学金", "category": "life-service"}, {"slug": "motorcycle-license-tianbao", "name": "摩托车驾照", "category": "life-service"}, {"slug": "veteran-subsidy-tianbao", "name": "退伍补贴", "category": "life-service"}, {"slug": "medical-account-sharing-tianbao", "name": "医保个人账户共济", "category": "life-service"}, {"slug": "huiminbao-claim-tianbao", "name": "惠民保理赔", "category": "life-service"}, {"slug": "flight-delay-claim-tianbao", "name": "航班延误险理赔", "category": "life-service"}, {"slug": "auto-claim-dispute-tianbao", "name": "车险定损争议", "category": "life-service"}, {"slug": "vehicle-scrapping-tianbao", "name": "车辆报废注销", "category": "life-service"}, {"slug": "etc-charge-dispute-tianbao", "name": "ETC扣费异常", "category": "life-service"}, {"slug": "night-highway-safety-tianbao", "name": "夜间高速安全", "category": "life-service"}, {"slug": "highway-accident-response-tianbao", "name": "事故高速处置", "category": "life-service"}, {"slug": "low-rent-housing-apply-tianbao", "name": "廉租房申请", "category": "life-service"}, {"slug": "flatmate-sharing-agreement-tianbao", "name": "合租分摊协议", "category": "life-service"}, {"slug": "falling-object-claim-tianbao", "name": "高空抛物维权", "category": "life-service"}, {"slug": "garbage-sorting-dispute-tianbao", "name": "垃圾分类争议", "category": "life-service"}, {"slug": "deceased-phone-transfer-tianbao", "name": "亲人去世手机号过户", "category": "life-service"}, {"slug": "game-account-inherit-tianbao", "name": "游戏账号继承", "category": "life-service"}, {"slug": "virtual-asset-inherit-tianbao", "name": "虚拟财产继承", "category": "life-service"}, {"slug": "xinxin-crime-risk-tianbao", "name": "帮信罪风险", "category": "life-service"}, {"slug": "facepay-risk-tianbao", "name": "刷脸支付风险", "category": "life-service"}, {"slug": "helmet-standard-tianbao", "name": "电动车头盔标准", "category": "life-service"}, {"slug": "legacy-support-agreement-tianbao", "name": "遗赠扶养协议", "category": "life-service"}, {"slug": "transfer-contract-pitfall-tianbao", "name": "转让合同避坑", "category": "life-service"}, {"slug": "child-labor-risk-tianbao", "name": "童工风险防范", "category": "life-service"}, {"slug": "tea-franchise-pitfall-tianbao", "name": "奶茶店加盟避坑", "category": "life-service"}, {"slug": "home-repair-scam-tianbao", "name": "上门维修防骗", "category": "life-service"}, {"slug": "ac-freon-scam-tianbao", "name": "空调加氟陷阱", "category": "life-service"}, {"slug": "waterproof-scam-tianbao", "name": "防水补漏骗局", "category": "life-service"}, {"slug": "cross-province-moving-tianbao", "name": "跨省搬家比价", "category": "life-service"}, {"slug": "moving-packing-tips-tianbao", "name": "搬家打包技巧", "category": "life-service"}, {"slug": "used-car-check-tianbao", "name": "二手车过户查验", "category": "life-service"}, {"slug": "farmland-subsidy-tianbao", "name": "耕地地力保护补贴", "category": "life-service"}, {"slug": "reforest-subsidy-tianbao", "name": "退耕还林补贴", "category": "life-service"}, {"slug": "poverty-monitor-aid-tianbao", "name": "脱贫监测户帮扶", "category": "life-service"}, {"slug": "poultry-farm-license-tianbao", "name": "养鸡场办证", "category": "life-service"}, {"slug": "greenhouse-subsidy-tianbao", "name": "大棚补贴", "category": "life-service"}, {"slug": "pig-insurance-claim-tianbao", "name": "生猪保险理赔", "category": "life-service"}, {"slug": "village-committee-election-tianbao", "name": "村委会选举", "category": "life-service"}, {"slug": "neighbor-land-dispute-tianbao", "name": "邻里占地纠纷", "category": "life-service"}, {"slug": "grave-dispute-tianbao", "name": "坟地纠纷", "category": "life-service"}, {"slug": "township-hospital-reimburse-tianbao", "name": "乡镇卫生院报销", "category": "life-service"}, {"slug": "township-market-stall-tianbao", "name": "乡镇集市摊位", "category": "life-service"}, {"slug": "rural-toilet-acceptance-tianbao", "name": "农村改厕验收", "category": "life-service"}, {"slug": "rural-broadband-tianbao", "name": "农村宽带办理", "category": "life-service"}, {"slug": "kinship-certificate-tianbao", "name": "亲属关系证明", "category": "life-service"}, {"slug": "lucky-money-amount-tianbao", "name": "压岁钱给多少", "category": "life-service"}, {"slug": "birthday-banquet-flow-tianbao", "name": "寿宴流程", "category": "life-service"}, {"slug": "funeral-gift-amount-tianbao", "name": "白事随礼标准", "category": "life-service"}, {"slug": "wheelchair-transfer-tianbao", "name": "轮椅转移技巧", "category": "life-service"}, {"slug": "roseola-care-tianbao", "name": "幼儿急疹护理", "category": "life-service"}, {"slug": "child-insurance-setup-tianbao", "name": "儿童保险配置", "category": "life-service"}, {"slug": "blocked-duct-relief-tianbao", "name": "堵奶处理", "category": "life-service"}, {"slug": "umbilical-care-tianbao", "name": "脐带护理", "category": "life-service"}, {"slug": "anemia-recipe-tianbao", "name": "贫血食谱", "category": "life-service"}, {"slug": "dysphagia-diet-tianbao", "name": "吞咽困难饮食", "category": "life-service"}, {"slug": "seat-select-tips-tianbao", "name": "值机选座技巧", "category": "life-service"}, {"slug": "air-miles-redeem-tianbao", "name": "航空里程兑换", "category": "life-service"}, {"slug": "metro-dispute-tianbao", "name": "地铁内纠纷", "category": "life-service"}, {"slug": "bike-theft-report-tianbao", "name": "自行车被盗报警", "category": "life-service"}, {"slug": "vehicle-agency-tianbao", "name": "代办车驾管", "category": "life-service"}, {"slug": "gov-hall-booking-tianbao", "name": "政务大厅预约", "category": "life-service"}, {"slug": "diploma-reissue-tianbao", "name": "毕业证丢失补办", "category": "life-service"}, {"slug": "dorm-inspection-appeal-tianbao", "name": "宿舍查寝申诉", "category": "life-service"}, {"slug": "fresh-graduate-status-tianbao", "name": "应届生身份保留", "category": "life-service"}, {"slug": "military-family-card-tianbao", "name": "军属优待证", "category": "life-service"}, {"slug": "major-medical-reimburse-tianbao", "name": "大病医保二次报销", "category": "life-service"}, {"slug": "bank-card-limit-restore-tianbao", "name": "银行卡降额恢复", "category": "life-service"}, {"slug": "travel-insurance-claim-tianbao", "name": "旅游险理赔", "category": "life-service"}, {"slug": "offsite-violation-handle-tianbao", "name": "违章异地处理", "category": "life-service"}, {"slug": "license-lottery-apply-tianbao", "name": "摇号购车", "category": "life-service"}, {"slug": "camera-ticket-appeal-tianbao", "name": "电子眼申诉", "category": "life-service"}, {"slug": "tibet-drive-prep-tianbao", "name": "车辆进藏准备", "category": "life-service"}, {"slug": "rental-filing-tianbao", "name": "租房备案登记", "category": "life-service"}, {"slug": "rental-lawsuit-tianbao", "name": "房屋租赁纠纷起诉", "category": "life-service"}, {"slug": "renovation-noise-complaint-tianbao", "name": "装修扰民投诉", "category": "life-service"}, {"slug": "parking-dispute-tianbao", "name": "停车位纠纷", "category": "life-service"}, {"slug": "community-canteen-tianbao", "name": "社区养老食堂", "category": "life-service"}, {"slug": "deceased-wechat-handle-tianbao", "name": "逝者微信账号处理", "category": "life-service"}, {"slug": "cloud-account-inherit-tianbao", "name": "网盘账号继承", "category": "life-service"}, {"slug": "livestream-fake-goods-tianbao", "name": "直播间买到假货", "category": "life-service"}, {"slug": "takedown-appeal-tianbao", "name": "删帖维权", "category": "life-service"}, {"slug": "bike-share-charge-tianbao", "name": "共享单车扣费争议", "category": "life-service"}, {"slug": "child-support-enforce-tianbao", "name": "抚养费执行", "category": "life-service"}, {"slug": "hygiene-license-tianbao", "name": "卫生许可证办理", "category": "life-service"}, {"slug": "shop-opening-checklist-tianbao", "name": "开店筹备清单", "category": "life-service"}, {"slug": "delivery-commission-compare-tianbao", "name": "美团饿了么抽成对比", "category": "life-service"}, {"slug": "store-supply-channel-tianbao", "name": "便利店进货渠道", "category": "life-service"}, {"slug": "appliance-repair-fee-tianbao", "name": "家电维修乱收费", "category": "life-service"}, {"slug": "drain-unclog-fee-tianbao", "name": "下水道疏通收费", "category": "life-service"}, {"slug": "pc-repair-data-save-tianbao", "name": "电脑维修数据保命", "category": "life-service"}, {"slug": "moving-damage-claim-tianbao", "name": "物品损坏索赔", "category": "life-service"}];
    log('待上传: '+LIST.length);
    let ok=0,skip=0,fail=0;
    for(let i=0;i<LIST.length;i++){
      const it=LIST[i];
      try{
        const gr=await fetch('https://fastly.jsdelivr.net/gh/yemugua/agent-skills@main/skills/'+it.category+'/'+it.slug+'/SKILL.md');
        if(!gr.ok){fail++;log('✗拉取 '+it.slug+' '+gr.status);continue;}
        const content=await gr.text();
        const b='----skh'+Date.now();
        const payload=JSON.stringify({slug:it.slug,displayName:it.name,version:'1.0.0',category:it.category});
        const body='--'+b+'\r\nContent-Disposition: form-data; name="payload"\r\n\r\n'+payload+'\r\n--'+b+'\r\nContent-Disposition: form-data; name="files"; filename="SKILL.md"\r\nContent-Type: text/markdown\r\n\r\n'+content+'\r\n--'+b+'--\r\n';
        const ur=await fetch(BASE+'/skills',{method:'POST',credentials:'include',headers:{'Content-Type':'multipart/form-data; boundary='+b},body});
        if(ur.ok){ok++;log('✓ '+(i+1)+' '+it.slug);}
        else if(ur.status===409){skip++;log('⊙已存在 '+it.slug);}
        else if(ur.status===429){log('⚠当日额度满，停止');break;}
        else{fail++;log('✗ '+it.slug+' '+ur.status);}
      }catch(e){fail++;log('✗ERR '+it.slug);}
      await sleep(1600);
    }
    log('== 上传完成 成功:'+ok+' 跳过:'+skip+' 失败:'+fail+' ==');
    log('…等2分钟让审核进单…');
    await sleep(120000);
    // 审发
    let pending=[],page=1;
    while(page<=200){
      const r=await fetch(BASE+'/admin/skills/reviews?page='+page+'&page_size=20',{credentials:'include'});
      if(!r.ok){log('队列读取失败 '+r.status);break;}
      const d=await r.json();
      const revs=d.reviews||[];
      if(!revs.length)break;
      for(const x of revs){const st=x.reviewStatus||x.status;if(st==='admin_review'||st==='pending')pending.push(x);}
      page++;await sleep(300);
    }
    log('待审: '+pending.length);
    let pok=0,pf=0;
    for(const s of pending){
      const slug=s.slug,ver=s.latestApprovedVersion||s.version||'1.0.0';
      try{
        const a=await fetch(BASE+'/admin/skills/'+slug+'/approve',{method:'POST',credentials:'include',headers:{'Content-Type':'application/json'},body:JSON.stringify({version:ver,note:'自动审核通过'})});
        if(!a.ok&&a.status!==409){pf++;log('✗审 '+slug+' '+a.status);continue;}
        await sleep(900);
        const p=await fetch(BASE+'/admin/skills/'+slug+'/publish-to-community',{method:'POST',credentials:'include',headers:{'Content-Type':'application/json'},body:JSON.stringify({publisherProfileId:3390})});
        if(p.ok||p.status===409){pok++;log('✓发布 '+slug);}else{pf++;log('✗发 '+slug+' '+p.status);}
        await sleep(900);
      }catch(e){pf++;log('✗ERR '+slug);}
    }
    log('★ 全部完成 上传:'+ok+' 发布:'+pok+' 失败:'+pf+' ★');
    window.__skhRunning=false;
  }catch(e){log('❌ '+e.message);window.__skhRunning=false;}
})();