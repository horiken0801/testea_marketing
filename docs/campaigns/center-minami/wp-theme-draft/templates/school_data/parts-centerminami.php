<?php
/**
 * センター南校 校舎ページ（parts-kugayama.php をベースに作成）
 *
 * ▼アップロード先
 *   wp-content/themes/testea/templates/school_data/parts-centerminami.php
 *
 * ▼このファイルを有効化するために category.php に追記が必要です（別途案内）
 *
 * ▼公開前に必ず対応してほしいTODO一覧
 *   1. $blog_cat_id … 「センター南校ブログ」カテゴリー作成後、そのカテゴリーIDに書き換える
 *   2. 電話番号・受付時間・最寄駅アクセスの詳細（住所は入力済み）
 *   3. 教室長メッセージ（決まり次第、写真と本文を差し替え）
 *   4. スライダー画像・道案内写真（現状すべてコメントアウトしています）
 *   5. 通塾エリア情報（決まり次第、久我山校等を参考に追記）
 */

// TODO: 「センター南校ブログ」カテゴリーを作成後、そのカテゴリーIDに変更してください
$blog_cat_id = 'XX';

// 住所（Googleマップ埋め込み用）
$center_minami_address = '神奈川県横浜市都筑区茅ケ崎中央44-14 SHOKENセンター南ビル202';
$center_minami_map_query = rawurlencode($center_minami_address);

// 公開準備が整うまでは管理者のみプレビューできるようにする。
// 公開する際は、この行を false にするか、この判定ブロックごと削除してください。
$center_minami_preview_only = true;
$center_minami_preview_allowed = $center_minami_preview_only
  ? (is_user_logged_in() && current_user_can('manage_options'))
  : true;
?>
<main>
  <section>
    <div class="ttl">
      <div class="ttl_main">
        <div class="row">
          <div class="ttl_main_tt">
            <h1>センター南校</h1>
            <p class="school-eyecatch-name" aria-hidden="true">センター南校</p>
            <div class="brecrumb">
              <ul>
                <li><a href="<?php echo home_url(); ?>">ホーム</a></li>
                <li>センター南校</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
      <figure>
        <!-- TODO: 校舎外観写真が用意でき次第、下記を差し替えてください（それまではロゴ等の共通画像を使用） -->
        <img src="<?php echo get_stylesheet_directory_uri() ?>/renew/common/images/logo@2x.png" alt="">
      </figure>
    </div>

    <div class="main">
      <div class="row">
        <div class="main_wrap">
          <?php get_sidebar(); ?>
          <div class="main_wrap_ct">
            <div class="detail">
              <?php if (!$center_minami_preview_allowed) : ?>

              <div id="sec">
                <div class="school-notice">
                  <div class="school-notice_item">
                    <p><b>【センター南校 準備中】</b></p>
                  </div>
                </div>
                <p style="text-align:left">
                  センター南校のページは現在準備中です。詳細が決まり次第、公開いたします。<br>
                  校舎に関するお問い合わせは<a href="<?php echo home_url('/inquiry/'); ?>">お問い合わせフォーム</a>よりお気軽にご連絡ください。
                </p>
              </div>

              <?php else : ?>

              <?php echo do_shortcode('[sc name="banner_school"][/sc]'); ?>

              <div id="sec">
                <div class="school-notice">
                  <div class="school-notice_item">
                    <p><b>【センター南校 開校準備中】</b></p>
                  </div>
                </div>
                <p style="text-align:left">
                  センター南校は現在、開校に向けて準備を進めております。教室の様子や講師紹介など、詳細が決まり次第このページで随時更新してまいります。<br>
                  無料相談・体験授業のお申込み、開校時期に関するお問い合わせはお気軽にご連絡ください。
                </p>
              </div>

              <!--
                TODO: 校舎写真が用意でき次第、久我山校の d_slider（swiper）ブロックを参考に
                画像スライダーをここに追加してください。
                画像アップロード先の目安: renew/school/images/centerminami/
              -->

              <!--
                TODO: Googleビジネスプロフィールの登録・レビューが集まり次第、
                久我山校の [grw id=XXXXX] ショートコードを参考にレビューエリアを追加してください。
              -->

              <div class="d_mess ic_mess">
                <h2>教室長からのメッセージ</h2>
                <div class="d_mess_profile">
                  <figure>
                    <!-- TODO: 教室長の写真に差し替えてください -->
                    <img src="<?php echo get_stylesheet_directory_uri() ?>/renew/teacher/images/noavatar.png" alt="">
                  </figure>
                  <div class="d_mess_profile_ct">
                    <h3><span>センター南校</span>教室長 近日公開</h3>
                    <p>
                      センター南校の教室長からのメッセージは近日公開予定です。今しばらくお待ちください。
                    </p>
                  </div>
                </div>
              </div>

              <div class="d_mem">
                <h2>センター南校の講師</h2>
                <ul id="return_teach">
                  <?php
                  $term = get_queried_object();
                  $teacher = apply_filters('get_teacher', $term->slug);
                  if ($teacher->have_posts()) :
                    while ($teacher->have_posts()) : $teacher->the_post();
                  ?>
                      <li>
                        <a href="<?php the_permalink(); ?>">
                          <figure>
                            <?php
                            $thumb = get_template_directory_uri() . '/renew/teacher/images/noavatar.png';
                            if (has_post_thumbnail()) {
                              $thumb =  get_the_post_thumbnail_url($post->ID, 'thumbnail');
                            }
                            ?>
                            <span><img src="<?php echo $thumb ?>" alt=""></span>
                            <figcaption><span><?php _e(get_post_meta($post->ID, 'pos', true)) ?></span><?php the_title(); ?></figcaption>
                          </figure>
                        </a>
                      </li>
                  <?php
                    endwhile;
                  else :
                  ?>
                    <li class="nopost">講師は近日公開予定です。</li>
                  <?php endif; ?>
                </ul>
                <?php wp_reset_query(); ?>
              </div>

              <div class="d_blog">
                <div class="sec_ttl">
                  <h2>センター南校のブログ</h2>
                  <a href="/school/centerminami/blog-cm" class="show_pc">センター南校ブログ一覧</a>
                </div>
                <div class="d_blog_list">
                  <ul>
                    <?php
                    $sticky = get_option('sticky_posts');
                    $the_query = new WP_Query(array(
                      'posts_per_page' => 1,
                      'post__in' => $sticky,
                      'cat' => $blog_cat_id
                    ));
                    if ($the_query->have_posts()) :
                      while ($the_query->have_posts()) :
                        $the_query->the_post(); ?>
                        <?php if (is_sticky()) : ?>
                          <li class="clearfix" id="sticky-post">
                            <a href="<?php the_permalink(); ?>">
                              <figure class="thumbList">
                                <?php if (has_post_thumbnail($post->ID)): ?>
                                  <img src="<?php echo get_the_post_thumbnail_url(); ?>" alt="">
                                <?php else : ?>
                                  <img src="<?php echo catch_thumbnail_image(); ?>" alt="">
                                <?php endif; ?>
                              </figure>
                              <p id="sticky-post">PICK UP!</p>
                              <h3><?php the_title(); ?></h3>
                            </a>
                          </li>
                        <?php endif; ?>
                      <?php endwhile; ?>
                      <?php wp_reset_postdata(); ?>
                    <?php else : ?>
                      <li class="nopost">注目記事はありません。</li>
                    <?php endif; ?>

                    <?php $args = array(
                      'posts_per_page' => 2,
                      'post__not_in' => $sticky,
                      'cat' => $blog_cat_id
                    );
                    ?>
                    <?php $the_query = new WP_Query($args); ?>
                    <?php if ($the_query->have_posts()) :
                      while ($the_query->have_posts()) : $the_query->the_post(); ?>
                        <li class="clearfix">
                          <a href="<?php the_permalink(); ?>">
                            <figure class="thumbList">
                              <?php if (has_post_thumbnail($post->ID)): ?>
                                <img src="<?php echo get_the_post_thumbnail_url(); ?>" alt="">
                              <?php else : ?>
                                <img src="<?php echo catch_thumbnail_image(); ?>" alt="">
                              <?php endif; ?>
                            </figure>
                            <time datetime="<?php echo get_the_date('Y-m-d'); ?>"><?php echo get_the_date('Y.m.d'); ?></time>
                            <h3><?php the_title(); ?></h3>
                          </a>
                        </li>
                      <?php endwhile; ?>
                      <?php wp_reset_postdata(); ?>
                    <?php else : ?>
                      <li class="nopost">最新情報はありません。</li>
                    <?php endif; ?>
                  </ul>
                </div>
              </div>

              <div class="d_blog">
                <div class="msg_ttl">
                  <h2>塾長からのメッセージ</h2>
                </div>
                <div class="d_blog_list">
                  <ul>
                    <?php $args = array(
                      'cat' => '56',
                      'post__in' => $sticky
                    );
                    ?>
                    <?php $the_query = new WP_Query($args); ?>
                    <?php if ($the_query->have_posts()) :
                      while ($the_query->have_posts()) : $the_query->the_post(); ?>
                        <li class="clearfix">
                          <a href="<?php the_permalink(); ?>">
                            <figure class="thumbList">
                              <?php if (has_post_thumbnail($post->ID)): ?>
                                <img src="<?php echo get_the_post_thumbnail_url(); ?>" alt="">
                              <?php else : ?>
                                <img src="<?php echo catch_thumbnail_image(); ?>" alt="">
                              <?php endif; ?>
                            </figure>
                            <time datetime="<?php echo get_the_date('Y-m-d'); ?>"></time>
                            <h3><?php the_title(); ?></h3>
                          </a>
                        </li>
                      <?php endwhile; ?>
                      <?php wp_reset_postdata(); ?>
                    <?php else : ?>
                      <li class="nopost">最新情報はありません。</li>
                    <?php endif; ?>
                  </ul>
                </div>
              </div>

              <div class="d_contact">
                <div class="d_list">
                  <dl>
                    <dt>住所</dt>
                    <dd>
                      〒224-0032<br>
                      <?php echo esc_html($center_minami_address); ?>
                      <!-- TODO: ビル名は変更予定とのことなので、確定次第更新してください -->
                    </dd>
                  </dl>
                  <dl>
                    <dt>電話番号</dt>
                    <dd>準備中<!-- TODO: 決定次第 <a href="tel:0X-XXXX-XXXX">0X-XXXX-XXXX</a> の形式に変更 --></dd>
                  </dl>
                  <dl>
                    <dt>受付時間</dt>
                    <dd>準備中<!-- TODO: 例）月～金14:00～22:00、土11:00～20:00 --></dd>
                  </dl>
                  <dl>
                    <dt>最寄駅</dt>
                    <dd>
                      横浜市営地下鉄ブルーライン・グリーンライン センター南駅
                      <!-- TODO: 出口・徒歩分数・目印などの詳細アクセスを追記してください -->
                    </dd>
                  </dl>
                </div>
                <div class="d_map">
                  <iframe
                    src="https://maps.google.com/maps?q=<?php echo $center_minami_map_query; ?>&z=16&output=embed"
                    frameborder="0" style="border:0" allowfullscreen></iframe>
                  <a href="https://www.google.com/maps/search/?api=1&query=<?php echo $center_minami_map_query; ?>" class="btn_top type01 type_blank" target="_blank"><span>GoogleMapで地図を見る</span></a>
                </div>
              </div>

              <!--
                TODO: 道案内（d_direct）は現地写真が撮影でき次第、
                久我山校の d_direct ブロックを参考に追加してください。
              -->

              <div class="d_area">
                <h2>センター南校の通塾エリア</h2>
                <p class="d_area_des">
                  TESTEA（テスティー）には、幅広い地域から生徒たちが中学受験・高校受験・大学受験・定期試験対策のために通ってきています。
                  センター南校の通塾エリア情報は近日公開予定です。
                </p>
                <!-- TODO: 駅名・住所・学校名からの通塾エリア情報が決まり次第、久我山校の d_area_bl ブロックを参考に追記してください -->
              </div>

              <?php endif; ?>
            </div>
            <?php get_template_part('renew/templates/templates', 'box') ?>
          </div>
        </div>
      </div>
    </div>
  </section>
</main>
